#!/bin/bash
# deployment.sh - Helper script for deployment

set -e

echo "=== Proxmox VM Deployment Script ==="

# Check if required files exist
if [ ! -f "users.csv" ]; then
    echo "Error: users.csv file not found!"
    echo "Please create users.csv with your user list"
    exit 1
fi

if [ ! -f "terraform.tfvars" ]; then
    echo "Error: terraform.tfvars not found!"
    echo "Please copy terraform.tfvars.example to terraform.tfvars and configure it"
    exit 1
fi

# Count users
USER_COUNT=$(grep -c "^[^#]" users.csv || true)
VM_COUNT=$((USER_COUNT * 3))

echo "Found $USER_COUNT users in CSV file"
echo "Will create $VM_COUNT VMs total"

# Initialize terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Plan deployment
echo "Creating deployment plan..."
terraform plan -out=tfplan

echo ""
echo "Plan summary:"
echo "- Users: $USER_COUNT"
echo "- Total VMs: $VM_COUNT"
echo "- VM ID range: 400-$((400 + VM_COUNT - 1))"

read -p "Do you want to proceed with deployment? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo "Deploying VMs..."
    terraform apply tfplan
    
    # Get the highest VM ID for reference
    HIGHEST_ID=$(terraform output -raw highest_vm_id)
    echo ""
    echo "Deployment complete!"
    echo "Highest VM ID used: $HIGHEST_ID"
    echo "Next VM ID to use: $((HIGHEST_ID + 1))"
    
    # Save the next ID for future reference
    echo $((HIGHEST_ID + 1)) > .next_vm_id
else
    echo "Deployment cancelled"
    rm -f tfplan
fi
