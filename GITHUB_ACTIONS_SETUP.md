# GitHub Actions Auto-Deployment Setup

This guide will help you set up automatic deployment to your Ubuntu server using GitHub Actions with a self-hosted runner.

## Prerequisites

- Ubuntu server with your collecting website already running
- GitHub repository for your code
- SSH access to your Ubuntu server

## Step 1: Install the GitHub Actions Runner

1. SSH into your Ubuntu server
2. Run the setup script:
   ```bash
   ./setup-github-runner.sh
   ```

## Step 2: Configure the Runner in GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** → **Actions** → **Runners**
3. Click **"New self-hosted runner"**
4. Select **Linux** and **x64**
5. Copy the configuration command that looks like:
   ```bash
   sudo -u actions-runner /home/actions-runner/actions-runner/config.sh --url https://github.com/YOURUSERNAME/collecting-website --token YOUR_TOKEN_HERE
   ```
6. Run this command on your Ubuntu server

## Step 3: Start the Runner Service

After configuring the runner, start the systemd service:

```bash
sudo systemctl enable github-runner
sudo systemctl start github-runner
sudo systemctl status github-runner
```

## Step 4: Test the Setup

1. Push a commit to your main/master branch
2. Check the **Actions** tab in your GitHub repository
3. You should see the workflow running
4. Once complete, your app will be automatically updated on your server

## How It Works

- **Trigger**: Workflow runs on every push to main/master branch
- **Runner**: Self-hosted runner on your Ubuntu server executes the deployment
- **Process**: 
  1. Checks out your latest code
  2. Installs Python dependencies
  3. Runs the deployment script
  4. Restarts your web service
  5. Verifies the deployment worked

## Files Created

- `.github/workflows/deploy.yml` - GitHub Actions workflow
- `deploy-github-actions.sh` - Deployment script optimized for GitHub Actions
- `setup-github-runner.sh` - Runner installation script

## Security Notes

- The runner connects outbound to GitHub (no inbound ports needed)
- Your server doesn't need to be exposed to the internet
- The runner runs as a dedicated `actions-runner` user
- Deployment happens with proper permissions

## Troubleshooting

- Check runner status: `sudo systemctl status github-runner`
- View runner logs: `sudo journalctl -u github-runner -f`
- Check deployment logs: `tail -f /var/log/collecting-website-deploy.log`
- Restart runner: `sudo systemctl restart github-runner`

## Manual Deployment

If you need to deploy manually, you can still use:
```bash
sudo ./deploy-local-simple.sh
```

Your automatic deployment is now ready! 🚀
