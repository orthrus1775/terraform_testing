#!/usr/bin/env python3
"""
VM Deployment Orchestrator for Proxmox Cluster
Manages Terraform deployments and Ansible configuration for multi-user VM environments
"""

import os
import sys
import json
import yaml
import csv
import logging
import subprocess
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
from jinja2 import Environment, FileSystemLoader

# Configuration and Data Classes
@dataclass
class VMTemplate:
    name: str
    vm_id: int
    os_type: str
    cpu_cores: int
    memory_mb: int
    disk_size_gb: int

@dataclass
class ProxmoxNode:
    name: str
    hostname: str
    available_cores: int
    available_memory_gb: int
    available_storage_gb: int
    current_load: float = 0.0

@dataclass
class User:
    username: str
    email: str
    full_name: str
    department: str
    vm_assignments: Dict[str, str] = None  # {vm_type: target_node}

@dataclass
class VMDeployment:
    user: User
    vm_type: str
    vm_id: int
    node: str
    ip_address: str
    status: str = "pending"

class DeploymentOrchestrator:
    def __init__(self, config_file: str = "config/settings.yaml"):
        self.config = self._load_config(config_file)
        self.setup_logging()
        self.templates = self._load_templates()
        self.nodes = self._load_nodes()
        self.users = []
        self.deployments = []
        
        # Jinja2 template environment
        self.jinja_env = Environment(
            loader=FileSystemLoader('templates'),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found")
            sys.exit(1)

    def setup_logging(self):
        """Configure logging"""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler(f"logs/deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

def get_next_available_vm_id(self, start_id: int = 500) -> int:
    """Query Proxmox for existing VM IDs and return next available ID"""
    try:
        # Query all nodes for existing VM IDs
        existing_ids = set()
        for node in self.nodes:
            cmd = [
                'pvesh', 'get', f'/nodes/{node.name}/qemu',
                '--output-format', 'json'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            vms = json.loads(result.stdout)
            for vm in vms:
                existing_ids.add(vm['vmid'])
        
        # Find next available ID starting from start_id
        current_id = start_id
        while current_id in existing_ids:
            current_id += 1
        
        return current_id
        
    except Exception as e:
        self.logger.warning(f"Could not query existing VM IDs: {e}")
        return start_id

    def _load_templates(self) -> Dict[str, VMTemplate]:
        """Load VM template configurations"""
        templates_config = self.config.get('vm_templates', {})
        templates = {}
        
        for template_name, template_config in templates_config.items():
            templates[template_name] = VMTemplate(
                name=template_config['name'],
                vm_id=template_config['vm_id'],
                os_type=template_config['os_type'],
                cpu_cores=template_config['cpu_cores'],
                memory_mb=template_config['memory_mb'],
                disk_size_gb=template_config['disk_size_gb']
            )
        
        return templates

    def _load_nodes(self) -> List[ProxmoxNode]:
        """Load Proxmox node configurations"""
        nodes_config = self.config.get('proxmox_nodes', [])
        nodes = []
        
        for node_config in nodes_config:
            nodes.append(ProxmoxNode(
                name=node_config['name'],
                hostname=node_config['hostname'],
                available_cores=node_config['available_cores'],
                available_memory_gb=node_config['available_memory_gb'],
                available_storage_gb=node_config['available_storage_gb']
            ))
        
        return nodes

    def load_users_from_csv(self, csv_file: str) -> List[User]:
        """Load users from CSV file"""
        users = []
        
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user = User(
                        username=row['username'].strip(),
                        email=row['email'].strip(),
                        full_name=row['full_name'].strip(),
                        department=row.get('department', '').strip()
                    )
                    users.append(user)
                    
            self.users = users
            self.logger.info(f"Loaded {len(users)} users from {csv_file}")
            return users
            
        except FileNotFoundError:
            self.logger.error(f"CSV file {csv_file} not found")
            raise
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            raise

    def calculate_load_distribution(self) -> Dict[str, List[User]]:
        """Calculate optimal user distribution across nodes"""
        total_users = len(self.users)
        vms_per_user = len(self.templates)
        total_vms = total_users * vms_per_user
        
        self.logger.info(f"Planning deployment: {total_users} users, {total_vms} VMs total")
        
        # Simple round-robin distribution for now
        node_assignments = {node.name: [] for node in self.nodes}
        node_names = [node.name for node in self.nodes]
        
        for i, user in enumerate(self.users):
            target_node = node_names[i % len(node_names)]
            node_assignments[target_node].append(user)
            
            # Assign VMs to nodes for this user
            user.vm_assignments = {}
            for j, vm_type in enumerate(self.templates.keys()):
                vm_node = node_names[(i + j) % len(node_names)]
                user.vm_assignments[vm_type] = vm_node
        
        return node_assignments

def generate_vm_ids(self, start_id: int = None) -> Dict[str, int]:
    """Generate unique VM IDs for deployment"""
    if start_id is None:
        start_id = self.get_next_available_vm_id(500)
    
    vm_id_map = {}
    current_id = start_id
    
    for user in self.users:
        for vm_type in self.templates.keys():
            vm_key = f"{user.username}_{vm_type}"
            vm_id_map[vm_key] = current_id
            current_id += 1
    
    return vm_id_map

    def create_terraform_configs(self, user_batch: List[User], batch_id: str) -> str:
        """Generate Terraform configuration files for a batch of users"""
        batch_dir = f"terraform_batches/batch_{batch_id}"
        os.makedirs(batch_dir, exist_ok=True)
        
        # Generate VM ID mapping
        vm_ids = self.generate_vm_ids()
        
        # Prepare template variables
        template_vars = {
            'users': user_batch,
            'vm_templates': self.templates,
            'vm_ids': vm_ids,
            'proxmox_config': self.config.get('proxmox', {}),
            'batch_id': batch_id
        }
        
        # Generate main.tf
        main_template = self.jinja_env.get_template('terraform/main.tf.j2')
        with open(f"{batch_dir}/main.tf", 'w') as f:
            f.write(main_template.render(template_vars))
        
        # Generate variables.tf
        variables_template = self.jinja_env.get_template('terraform/variables.tf.j2')
        with open(f"{batch_dir}/variables.tf", 'w') as f:
            f.write(variables_template.render(template_vars))
        
        # Generate terraform.tfvars
        tfvars_template = self.jinja_env.get_template('terraform/terraform.tfvars.j2')
        with open(f"{batch_dir}/terraform.tfvars", 'w') as f:
            f.write(tfvars_template.render(template_vars))
        
        self.logger.info(f"Generated Terraform configs for batch {batch_id}")
        return batch_dir

    def deploy_terraform_batch(self, batch_dir: str) -> bool:
        """Deploy a batch using Terraform"""
        try:
            original_cwd = os.getcwd()
            os.chdir(batch_dir)
            
            # Initialize Terraform
            result = subprocess.run(['terraform', 'init'], 
                                  capture_output=True, text=True, check=True)
            self.logger.info(f"Terraform init successful: {result.stdout}")
            
            # Plan deployment
            result = subprocess.run(['terraform', 'plan', '-out=tfplan'], 
                                  capture_output=True, text=True, check=True)
            self.logger.info(f"Terraform plan successful")
            
            # Apply deployment
            result = subprocess.run(['terraform', 'apply', 'tfplan'], 
                                  capture_output=True, text=True, check=True)
            self.logger.info(f"Terraform apply successful: {result.stdout}")
            
            # Get outputs
            result = subprocess.run(['terraform', 'output', '-json'], 
                                  capture_output=True, text=True, check=True)
            outputs = json.loads(result.stdout)
            
            # Save outputs for Ansible
            with open('terraform_outputs.json', 'w') as f:
                json.dump(outputs, f, indent=2)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Terraform deployment failed: {e.stderr}")
            return False
        finally:
            os.chdir(original_cwd)

    def generate_ansible_inventory(self, batch_dir: str) -> str:
        """Generate Ansible inventory from Terraform outputs"""
        try:
            with open(f"{batch_dir}/terraform_outputs.json", 'r') as f:
                terraform_outputs = json.load(f)
            
            # Generate inventory
            inventory_template = self.jinja_env.get_template('ansible/inventory.j2')
            inventory_content = inventory_template.render({
                'terraform_outputs': terraform_outputs,
                'templates': self.templates
            })
            
            inventory_file = f"{batch_dir}/inventory.yml"
            with open(inventory_file, 'w') as f:
                f.write(inventory_content)
            
            self.logger.info(f"Generated Ansible inventory: {inventory_file}")
            return inventory_file
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ansible inventory: {e}")
            raise

    def run_ansible_playbooks(self, inventory_file: str, batch_dir: str) -> bool:
        """Run Ansible playbooks for VM configuration"""
        playbook_dir = self.config.get('ansible', {}).get('playbook_dir', 'ansible')
        
        playbooks = [
            'base_configuration.yml',
            'guacamole_integration.yml',
            'netbox_integration.yml',
            'freeipa_integration.yml'
        ]
        
        try:
            for playbook in playbooks:
                playbook_path = f"{playbook_dir}/{playbook}"
                if not os.path.exists(playbook_path):
                    self.logger.warning(f"Playbook not found: {playbook_path}")
                    continue
                
                cmd = [
                    'ansible-playbook',
                    '-i', inventory_file,
                    playbook_path,
                    '--extra-vars', f"batch_dir={batch_dir}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info(f"Successfully ran playbook {playbook}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ansible playbook failed: {e.stderr}")
            return False

    def deploy_batch(self, user_batch: List[User], batch_id: str) -> bool:
        """Deploy a complete batch of users"""
        self.logger.info(f"Starting deployment for batch {batch_id} with {len(user_batch)} users")
        
        try:
            # Generate Terraform configs
            batch_dir = self.create_terraform_configs(user_batch, batch_id)
            
            # Deploy with Terraform
            if not self.deploy_terraform_batch(batch_dir):
                raise Exception("Terraform deployment failed")
            
            # Generate Ansible inventory
            inventory_file = self.generate_ansible_inventory(batch_dir)
            
            # Configure with Ansible
            if not self.run_ansible_playbooks(inventory_file, batch_dir):
                raise Exception("Ansible configuration failed")
            
            self.logger.info(f"Successfully completed batch {batch_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Batch {batch_id} deployment failed: {e}")
            return False

    def deploy_all_users(self, batch_size: int = 15) -> Dict[str, bool]:
        """Deploy VMs for all users in batches"""
        self.logger.info(f"Starting deployment for {len(self.users)} users in batches of {batch_size}")
        
        # Calculate load distribution
        load_distribution = self.calculate_load_distribution()
        
        # Create user batches
        user_batches = []
        for i in range(0, len(self.users), batch_size):
            batch = self.users[i:i + batch_size]
            user_batches.append((batch, f"batch_{i // batch_size + 1:03d}"))
        
        # Deploy batches
        results = {}
        for batch_users, batch_id in user_batches:
            success = self.deploy_batch(batch_users, batch_id)
            results[batch_id] = success
            
            if not success:
                self.logger.error(f"Batch {batch_id} failed, stopping deployment")
                break
        
        return results

    def generate_deployment_report(self, results: Dict[str, bool]) -> str:
        """Generate deployment summary report"""
        report_template = self.jinja_env.get_template('reports/deployment_summary.j2')
        
        total_batches = len(results)
        successful_batches = sum(results.values())
        failed_batches = total_batches - successful_batches
        
        report_content = report_template.render({
            'timestamp': datetime.now(),
            'total_users': len(self.users),
            'total_batches': total_batches,
            'successful_batches': successful_batches,
            'failed_batches': failed_batches,
            'batch_results': results
        })
        
        report_file = f"reports/deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        os.makedirs('reports', exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        self.logger.info(f"Generated deployment report: {report_file}")
        return report_file

def main():
    parser = argparse.ArgumentParser(description='VM Deployment Orchestrator')
    parser.add_argument('--config', default='config/settings.yaml', 
                       help='Configuration file path')
    parser.add_argument('--users-csv', required=True, 
                       help='CSV file containing user information')
    parser.add_argument('--batch-size', type=int, default=15, 
                       help='Number of users per deployment batch')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Generate configs without deploying')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = DeploymentOrchestrator(args.config)
    
    # Load users
    orchestrator.load_users_from_csv(args.users_csv)
    
    if args.dry_run:
        # Generate configs only
        orchestrator.logger.info("Dry run mode - generating configurations only")
        load_distribution = orchestrator.calculate_load_distribution()
        print(f"Would deploy {len(orchestrator.users)} users across {len(orchestrator.nodes)} nodes")
        
        # Generate sample batch
        sample_batch = orchestrator.users[:min(5, len(orchestrator.users))]
        sample_batch_dir = orchestrator.create_terraform_configs(sample_batch, "sample")
        print(f"Sample configuration generated in: {sample_batch_dir}")
    else:
        # Full deployment
        results = orchestrator.deploy_all_users(args.batch_size)
        report_file = orchestrator.generate_deployment_report(results)
        
        print(f"Deployment completed. Report: {report_file}")
        
        # Exit with appropriate code
        if not all(results.values()):
            sys.exit(1)

if __name__ == "__main__":
    main()
