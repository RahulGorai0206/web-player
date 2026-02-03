#!/usr/bin/env python3
import os
import re
import json
import argparse
import sys
import subprocess
from pathlib import Path
from collections import defaultdict, deque

# Configuration
REPO_ROOT = "."
TF_ROOT = "infrastructure/IAC/Terraform"

class HCLParser:
    """
    A simple, robust HCL parser for specific Terraform constructs.
    Used to extract backend config and remote state config, which terraform-config-inspect misses.
    """
    
    def __init__(self):
        self.kv_re = re.compile(r'^\s*([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']')

    def parse_tfvars(self, file_path):
        vars = {}
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or line.startswith('//'):
                        continue
                    match = self.kv_re.match(line)
                    if match:
                        vars[match.group(1)] = match.group(2)
        except Exception:
            pass
        return vars

    def parse_variables_tf(self, file_path):
        """Parse variables.tf to extract default values."""
        defaults = {}
        try:
            content = file_path.read_text(encoding='utf-8')
            tokens = self._tokenize(content)
            it = iter(tokens)
            
            while True:
                token = next(it)
                if token == 'variable':
                    var_name = next(it)
                    if var_name.startswith('"') and var_name.endswith('"'):
                        var_name = var_name[1:-1]
                    
                    # Parse body to find default
                    default_val = self._parse_variable_body(it)
                    if default_val is not None:
                        defaults[var_name] = default_val
        except StopIteration:
            pass
        except Exception:
            pass
        return defaults

    def _parse_variable_body(self, it):
        """Parse variable body { ... } and return default value if present."""
        # Expect {
        while True:
            t = next(it)
            if t == '{': break
        
        default_val = None
        depth = 1
        while depth > 0:
            token = next(it)
            if token == '{':
                depth += 1
            elif token == '}':
                depth -= 1
            elif token == 'default':
                if next(it) == '=':
                    val = next(it)
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    default_val = val
        return default_val

    def extract_backend_config(self, content):
        tokens = self._tokenize(content)
        it = iter(tokens)
        try:
            while True:
                token = next(it)
                if token == 'backend' and next(it) == '"gcs"':
                    return self._parse_block_body(it, ['bucket', 'prefix'])
        except StopIteration:
            pass
        return None

    def extract_remote_state_config(self, file_path, line_num, vars):
        """
        Extract config block from terraform_remote_state data source.
        Reads the file and looks around the specified line number.
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            # Start tokenizing from the given line (0-indexed)
            # We give a bit of buffer before just in case
            start_line = max(0, line_num - 2)
            relevant_content = '\n'.join(lines[start_line:])
            
            tokens = self._tokenize(relevant_content)
            it = iter(tokens)
            
            # We expect: data "terraform_remote_state" "name" { ... }
            # But since we start near the definition, we might just see the body or the header.
            # Let's just look for 'config' = { ... } inside the first block we find?
            # Or better, just look for 'config' block.
            
            while True:
                token = next(it)
                if token == 'config':
                    if next(it) == '=':
                        config = self._parse_config_block(it)
                        if config:
                            bucket = self._resolve_value(config.get('bucket'), vars)
                            prefix = self._resolve_value(config.get('prefix'), vars)
                            if bucket and prefix:
                                return (bucket, prefix)
                        return None
        except StopIteration:
            pass
        except Exception:
            pass
        return None

    def _tokenize(self, content):
        lines = [line for line in content.splitlines() if not line.strip().startswith(('#', '//'))]
        clean_content = '\n'.join(lines)
        token_re = re.compile(r'(".*?"|{|} |=|\S+)')
        return [t for t in token_re.findall(clean_content) if t.strip()]

    def _parse_block_body(self, it, keys_to_find):
        while True:
            t = next(it)
            if t == '{': break
        
        found = {}
        depth = 1
        while depth > 0:
            token = next(it)
            if token == '{':
                depth += 1
            elif token == '}':
                depth -= 1
            elif token in keys_to_find:
                if next(it) == '=':
                    val = next(it)
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    found[token] = val
        
        if all(k in found for k in keys_to_find):
            return tuple(found[k] for k in keys_to_find)
        return None

    def _parse_config_block(self, it):
        while True:
            t = next(it)
            if t == '{': break
        
        config = {}
        depth = 1
        while depth > 0:
            token = next(it)
            if token == '{':
                depth += 1
            elif token == '}':
                depth -= 1
            elif token in ['bucket', 'prefix']:
                if next(it) == '=':
                    val = next(it)
                    config[token] = val
        return config

    def _resolve_value(self, val, vars):
        if not val:
            return None
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        if val.startswith('var.'):
            var_name = val.split('.')[1]
            return vars.get(var_name)
        return None


class TerraformDependencyMapper:
    def __init__(self, repo_root):
        self.repo_root = Path(repo_root).resolve()
        self.tf_root = self.repo_root / TF_ROOT
        self.nodes = set()
        self.edges = defaultdict(set)
        self.rev_edges = defaultdict(set)
        self.backend_map = {}
        self.parser = HCLParser()

    def find_tf_dirs(self):
        for root, dirs, files in os.walk(self.tf_root):
            if any(f.endswith('.tf') for f in files):
                rel_path = Path(root).relative_to(self.repo_root)
                self.nodes.add(str(rel_path))

    def build_backend_index(self):
        for node in self.nodes:
            dir_path = self.repo_root / node
            for tf_file in dir_path.glob('*.tf'):
                try:
                    content = tf_file.read_text(encoding='utf-8')
                    backend = self.parser.extract_backend_config(content)
                    if backend:
                        self.backend_map[backend] = node
                        break
                except Exception:
                    pass

    def get_dir_vars(self, dir_path):
        vars = {}
        # Check all .tf files for variable defaults
        for f in dir_path.glob('*.tf'):
            vars.update(self.parser.parse_variables_tf(f))
        # Overwrite with tfvars
        tfvars_path = dir_path / 'terraform.tfvars'
        if tfvars_path.exists():
            vars.update(self.parser.parse_tfvars(tfvars_path))
        for f in dir_path.glob('*.auto.tfvars'):
            vars.update(self.parser.parse_tfvars(f))
        return vars

    def parse_directory(self, dir_path_str):
        dir_path = self.repo_root / dir_path_str
        dependencies = set()
        
        if not dir_path.exists():
            return dependencies

        # Run terraform-config-inspect
        try:
            result = subprocess.run(
                ["terraform-config-inspect", "--json", str(dir_path)],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            # Fallback or skip if tool missing/fails
            return dependencies

        # 1. Module Calls
        if "module_calls" in data:
            for mod_name, mod_data in data["module_calls"].items():
                source = mod_data.get("source", "")
                if source.startswith('.') or source.startswith('/'):
                    if source.startswith('/'):
                        target_path = Path(source)
                    else:
                        target_path = (dir_path / source).resolve()
                    
                    try:
                        rel_target = target_path.relative_to(self.repo_root)
                        dependencies.add(str(rel_target))
                    except ValueError:
                        pass

        # 2. Remote States
        if "data_resources" in data:
            vars = None # Lazy load vars only if needed
            for dr_key, dr_data in data["data_resources"].items():
                if dr_data.get("type") == "terraform_remote_state":
                    if vars is None:
                        vars = self.get_dir_vars(dir_path)
                    
                    # Use custom parser to extract config
                    pos = dr_data.get("pos", {})
                    filename = pos.get("filename")
                    line = pos.get("line", 1)
                    
                    if filename:
                        # filename from inspect is relative to the inspected dir usually?
                        # Let's check. The output showed "IAC/Terraform/..." which is relative to CWD.
                        # So we can use it directly relative to repo root.
                        file_path = self.repo_root / filename
                        if file_path.exists():
                            remote_state = self.parser.extract_remote_state_config(file_path, line, vars)
                            if remote_state:
                                bucket, prefix = remote_state
                                if (bucket, prefix) in self.backend_map:
                                    dependencies.add(self.backend_map[(bucket, prefix)])

        return dependencies

    def build_graph(self):
        self.find_tf_dirs()
        self.build_backend_index()
        
        for node in self.nodes:
            deps = self.parse_directory(node)
            for dep in deps:
                if dep in self.nodes:
                    self.edges[node].add(dep)
                    self.rev_edges[dep].add(node)
                elif (self.repo_root / dep).exists():
                    self.nodes.add(dep)
                    self.edges[node].add(dep)
                    self.rev_edges[dep].add(node)

    def get_affected_nodes(self, changed_files):
        initial_nodes = set()
        for f in changed_files:
            f_path = self.repo_root / f
            if not f_path.exists():
                continue
            
            if f.endswith('.tf') or f.endswith('.tfvars'):
                parent = str(Path(f).parent)
                if parent in self.nodes:
                    initial_nodes.add(parent)

        affected = set(initial_nodes)
        queue = deque(initial_nodes)
        
        while queue:
            current = queue.popleft()
            consumers = self.rev_edges[current]
            for consumer in consumers:
                if consumer not in affected:
                    affected.add(consumer)
                    queue.append(consumer)
        
        return list(affected)

    def filter_runnable_targets(self, nodes):
        """
        Filter nodes to only return those that are 'root' modules meant to be applied.
        Criteria:
        1. Must be in infrastructure/IAC/Terraform/env/
        2. Must NOT be in a 'modules' subdirectory relative to the env root.
        3. Must contain a 'backend.tf' file (strong indicator of a root module).
        """
        targets = []
        for node in nodes:
            # 1. Basic path check
            if not node.startswith("infrastructure/IAC/Terraform/env/"):
                continue
            
            # 2. 'modules' check
            # Avoid matching "modules" as a substring in a directory name (e.g. "k8s-modules-app")
            # We want to exclude paths that have "modules" as a directory component.
            if "modules" in Path(node).parts:
                continue

            # 3. backend.tf check
            # Construct full path to check for file existence
            node_path = self.repo_root / node
            if (node_path / "backend.tf").exists():
                targets.append(node)
            
        return targets

    def to_json(self):
        return {
            "nodes": list(self.nodes),
            "edges": {k: list(v) for k, v in self.edges.items()}
        }

def main():
    parser = argparse.ArgumentParser(description="Terraform Dependency Mapper")
    parser.add_argument("--changed-files", help="Path to file containing list of changed files")
    parser.add_argument("--files", nargs="+", help="List of changed files passed as arguments")
    parser.add_argument("--output", choices=["json", "matrix"], default="json", help="Output format")
    parser.add_argument("--graph-output", help="File to write the full graph JSON to")
    parser.add_argument("--all", action="store_true", help="Run all stacks")
    parser.add_argument("--targets", nargs="+", help="List of specific stacks to run")
    parser.add_argument("--env", help="Filter stacks by environment (e.g. dev, prod-us, prod-eu)")
    
    args = parser.parse_args()

    # Check if terraform-config-inspect is available
    try:
        subprocess.run(["terraform-config-inspect", "--version"], capture_output=True, check=False)
    except FileNotFoundError:
        print("Error: terraform-config-inspect not found in PATH.", file=sys.stderr)
        sys.exit(1)

    mapper = TerraformDependencyMapper(REPO_ROOT)
    mapper.build_graph()

    if args.graph_output:
        with open(args.graph_output, 'w') as f:
            json.dump(mapper.to_json(), f, indent=2)

    runnable_targets = []

    if args.all:
        runnable_targets = mapper.filter_runnable_targets(mapper.nodes)
    elif args.targets:
        runnable_targets = mapper.filter_runnable_targets(args.targets)
    else:
        changed_files = []
        if args.changed_files:
            try:
                with open(args.changed_files, 'r') as f:
                    content = f.read().strip()
                    # Try parsing as JSON first
                    try:
                        json_files = json.loads(content)
                        if isinstance(json_files, list):
                            changed_files.extend(json_files)
                        else:
                            # Fallback for non-list JSON (unlikely but safe)
                            pass
                    except json.JSONDecodeError:
                        # Fallback to line-based parsing
                        changed_files.extend([line.strip() for line in content.splitlines() if line.strip()])
            except Exception as e:
                print(f"Error reading changed files: {e}", file=sys.stderr)
        
        if args.files:
            changed_files.extend(args.files)

        if changed_files:
            affected_nodes = mapper.get_affected_nodes(changed_files)
            runnable_targets = mapper.filter_runnable_targets(affected_nodes)

    if runnable_targets:
        if args.env:
            filtered_targets = []
            for target in runnable_targets:
                parts = Path(target).parts
                if len(parts) > 3 and parts[2] == "env" and parts[3] == args.env:
                    filtered_targets.append(target)
            runnable_targets = filtered_targets

        if args.output == "matrix":
            matrix = []
            for target in runnable_targets:
                parts = Path(target).parts
                if len(parts) > 3 and parts[2] == "env":
                    env = parts[3]
                    matrix.append({"dir": target, "env": env})
            print(json.dumps(matrix))
        else:
            print(json.dumps(runnable_targets, indent=2))

if __name__ == "__main__":
    main()
