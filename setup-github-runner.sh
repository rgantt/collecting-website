#!/bin/bash

# GitHub Actions Self-Hosted Runner Setup Script
# Run this on your Ubuntu server to set up automatic deployments

set -e

echo "🚀 Setting up GitHub Actions Self-Hosted Runner..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Don't run this script as root. Use a regular user account."
    exit 1
fi

# Create actions-runner user if it doesn't exist
if ! id "actions-runner" &>/dev/null; then
    echo "👤 Creating actions-runner user..."
    sudo useradd -m -s /bin/bash actions-runner
    sudo usermod -aG sudo actions-runner
fi

# Create runner directory
RUNNER_DIR="/home/actions-runner/actions-runner"
sudo mkdir -p $RUNNER_DIR
sudo chown actions-runner:actions-runner $RUNNER_DIR

echo "📦 Downloading GitHub Actions Runner..."

# Download the latest runner
cd /tmp
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Verify the hash (optional but recommended)
echo "29fc8cf2dab4c195bb147384e7e2c94cfd4d4022c793b346a6175435265aa278  actions-runner-linux-x64-2.311.0.tar.gz" | shasum -a 256 -c

# Extract to runner directory
sudo tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz -C $RUNNER_DIR
sudo chown -R actions-runner:actions-runner $RUNNER_DIR

echo "🔧 Installing dependencies..."
sudo $RUNNER_DIR/bin/installdependencies.sh

# Set up permissions for the app directory
APP_DIR="/var/www/collecting-website"
sudo mkdir -p $APP_DIR
sudo chown -R actions-runner:www-data $APP_DIR
sudo chmod -R 775 $APP_DIR

# Add actions-runner to www-data group
sudo usermod -aG www-data actions-runner

# Create systemd service for the runner
echo "📝 Creating systemd service..."
sudo tee /etc/systemd/system/github-runner.service > /dev/null <<EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=actions-runner
WorkingDirectory=/home/actions-runner/actions-runner
ExecStart=/home/actions-runner/actions-runner/run.sh
Restart=always
RestartSec=5
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=5min

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Setup complete!"
echo ""
echo "🔗 Next steps:"
echo "1. Go to your GitHub repository → Settings → Actions → Runners"
echo "2. Click 'New self-hosted runner'"
echo "3. Select Linux x64"
echo "4. Copy the configuration command that looks like:"
echo "   sudo -u actions-runner $RUNNER_DIR/config.sh --url https://github.com/yourusername/collecting-website --token YOUR_TOKEN"
echo ""
echo "5. After configuration, enable and start the service:"
echo "   sudo systemctl enable github-runner"
echo "   sudo systemctl start github-runner"
echo "   sudo systemctl status github-runner"
echo ""
echo "6. The runner will now automatically deploy your app when you push to main/master!"
