#!/bin/bash

# Quick fix script for www-data home directory
# Run this with sudo to fix AWS CLI permissions

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

echo "Creating proper home directory for www-data user..."

# Create home directory for www-data user
mkdir -p /var/lib/www-data
chown www-data:www-data /var/lib/www-data
chmod 755 /var/lib/www-data

# Create .aws directory for AWS CLI config
mkdir -p /var/lib/www-data/.aws
chown www-data:www-data /var/lib/www-data/.aws
chmod 700 /var/lib/www-data/.aws

echo "✅ Fixed www-data home directory. You can now run the deployment script again."
echo "💡 If you have AWS credentials, copy them to /var/lib/www-data/.aws/"
