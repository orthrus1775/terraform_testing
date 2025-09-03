#!/bin/bash
# check_security.sh - Verify repository security before committing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

SECURITY_ISSUES=0

print_status "Security Check for Terraform Repository"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "Not a git repository. Run this from your terraform project directory."
    exit 1
fi

# Check if .gitignore exists
if [ ! -f ".gitignore" ]; then
    print_error ".gitignore file missing!"
    ((SECURITY_ISSUES++))
else
    print_success ".gitignore file exists"
fi

# Check critical patterns in .gitignore
print_status "Checking .gitignore patterns"

REQUIRED_PATTERNS=(
    "terraform.tfvars"
    "*.tfstate"
    "*.tfplan"
    ".terraform/"
    "*.log"
)

for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if grep -q "$pattern" .gitignore 2>/dev/null; then
        print_success "$pattern is ignored"
    else
        print_error "$pattern is NOT ignored"
        ((SECURITY_ISSUES++))
    fi
done

# Check for sensitive files in staging area
print_status "Checking staged files for sensitive data"

STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
if [ -n "$STAGED_FILES" ]; then
    echo "Staged files to be committed:"
    echo "$STAGED_FILES"
    echo ""
    
    # Check for sensitive file patterns
    SENSITIVE_PATTERNS=(
        "\.tfvars$"
        "\.tfstate"
        "\.tfplan"
        "\.pem$"
        "\.ppk$"
        "id_rsa"
        "\.log$"
    )
    
    for file in $STAGED_FILES; do
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            if echo "$file" | grep -E "$pattern" >/dev/null; then
                print_error "Sensitive file in staging: $file"
                ((SECURITY_ISSUES++))
            fi
        done
    done
    
    if [ $SECURITY_ISSUES -eq 0 ]; then
        print_success "No sensitive files in staging area"
    fi
else
    print_warning "No files staged for commit"
fi

# Check for terraform.tfvars in working directory
if [ -f "terraform.tfvars" ]; then
    if git check-ignore terraform.tfvars >/dev/null 2>&1; then
        print_success "terraform.tfvars exists but is properly ignored"
    else
        print_error "terraform.tfvars exists but is NOT ignored!"
        ((SECURITY_ISSUES++))
    fi
fi

# Check for API tokens in committed files
print_status "Scanning committed files for potential secrets"

# Look for common secret patterns in tracked files
SECRET_PATTERNS=(
    "api[_-]?token[_-]?secret"
    "password\s*=\s*[\"'][^\"']{8,}"
    "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    "proxmox[_-]?password"
    "pm[_-]?pass"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if git grep -i "$pattern" -- "*.tf" "*.tfvars.example" "*.sh" "*.md" 2>/dev/null | grep -v "your-" | grep -v "example-" | grep -v "changeme" | grep -v "template" >/dev/null; then
        print_warning "Potential secret pattern found: $pattern"
        git grep -i "$pattern" -- "*.tf" "*.tfvars.example" "*.sh" "*.md" 2>/dev/null | grep -v "your-" | grep -v "example-" | grep -v "changeme" | grep -v "template" || true
        echo ""
    fi
done

# Check file permissions
print_status "Checking file permissions"
if [ -f "terraform.tfvars" ]; then
    PERMS=$(stat -c "%a" terraform.tfvars)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "640" ]; then
        print_success "terraform.tfvars has secure permissions ($PERMS)"
    else
        print_warning "terraform.tfvars has loose permissions ($PERMS). Recommend: chmod 600 terraform.tfvars"
    fi
fi

# Check for environment variables in shell history
print_status "Environment Variable Security Check"
if [ -f ~/.bash_history ]; then
    if grep -q "export.*API.*TOKEN" ~/.bash_history 2>/dev/null; then
        print_warning "API tokens found in bash history. Consider: history -c"
    fi
fi

# Check remote repository settings
print_status "Remote Repository Check"
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -n "$REMOTE_URL" ]; then
    print_success "Remote repository: $REMOTE_URL"
    if echo "$REMOTE_URL" | grep -q "github.com"; then
        print_warning "Ensure your GitHub repository is set to PRIVATE"
    fi
else
    print_warning "No remote repository configured"
fi

# Summary
echo ""
if [ $SECURITY_ISSUES -eq 0 ]; then
    print_success "Security check passed! Repository is secure for commit."
    echo ""
    print_status "Safe to proceed with:"
    echo "git add ."
    echo "git commit -m 'Your commit message'"
    echo "git push origin main"
else
    print_error "Security issues found: $SECURITY_ISSUES"
    echo ""
    print_status "Fix these issues before committing:"
    echo "1. Update .gitignore to exclude sensitive files"
    echo "2. Remove sensitive files from staging: git reset HEAD <file>"
    echo "3. Move secrets to terraform.tfvars (which is ignored)"
    echo "4. Use terraform.tfvars.example for templates only"
    echo ""
    print_error "DO NOT COMMIT until these issues are resolved!"
    exit 1
fi

# Additional recommendations
echo ""
print_status "Security Recommendations:"
echo "• Always use terraform.tfvars.example as a template"
echo "• Store real credentials only in terraform.tfvars (ignored)"
echo "• Use environment variables for CI/CD pipelines"
echo "• Regularly rotate API tokens with ./scripts/manage_api_token.sh"
echo "• Review all commits before pushing to remote repository"
