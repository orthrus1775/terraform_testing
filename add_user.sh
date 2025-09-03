#!/bin/bash
# add_user.sh - Script to add a new user

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <username>"
    echo "Example: $0 john.d.smith"
    exit 1
fi

NEW_USER="$1"

# Validate username format
if [[ ! "$NEW_USER" =~ ^[a-z]+\.[a-z]\.[a-z]+$ ]]; then
    echo "Error: Username must be in format: first.mi.lastname (lowercase)"
    exit 1
fi

# Check if user already exists
if grep -q "^$NEW_USER$" users.csv; then
    echo "Error: User $NEW_USER already exists in users.csv"
    exit 1
fi

# Add user to CSV
echo "$NEW_USER" >> users.csv

echo "Added user: $NEW_USER"

# Get next VM ID
if [ -f ".next_vm_id" ]; then
    NEXT_ID=$(cat .next_vm_id)
else
    # Fallback: calculate from existing state
    if [ -f "terraform.tfstate" ]; then
        HIGHEST_ID=$(terraform output -raw highest_vm_id 2>/dev/null || echo "399")
        NEXT_ID=$((HIGHEST_ID + 1))
    else
        NEXT_ID=400
    fi
fi

echo "Next VM IDs will be: $NEXT_ID, $((NEXT_ID + 1)), $((NEXT_ID + 2))"

# Plan and apply changes
echo "Planning deployment for new user..."
terraform plan

read -p "Deploy VMs for $NEW_USER? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    terraform apply -auto-approve
    
    HIGHEST_ID=$(terraform output -raw highest_vm_id)
    echo $((HIGHEST_ID + 1)) > .next_vm_id
    
    echo "Successfully deployed VMs for user: $NEW_USER"
else
    echo "Deployment cancelled"
fi
