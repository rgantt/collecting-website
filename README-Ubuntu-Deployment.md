# Ubuntu Server Deployment Guide (Local Network)

This guide explains how to deploy your collecting website on a self-hosted Ubuntu server for local network access.

## 🚀 Quick Start

### 1. Server Setup (One-time)

On your Ubuntu server, run the setup script:

```bash
sudo ./setup-ubuntu-server.sh
```

This script will:
- Install required packages (Python, Nginx, etc.)
- Create necessary users and directories
- Configure firewall and Nginx
- Set up proper permissions

### 2. Initial Deployment

1. **Copy your codebase to the server**:
   ```bash
   sudo cp -r /path/to/your/collecting-website /opt/collecting-website
   # OR clone from GitHub:
   sudo git clone https://github.com/rgantt/collecting-website.git /opt/collecting-website
   ```

2. **Set up environment variables**:
   ```bash
   sudo cp /opt/collecting-website/.env.example /opt/collecting-website/.env
   sudo nano /opt/collecting-website/.env  # Edit with your values
   ```

3. **Run initial deployment**:
   ```bash
   sudo /opt/collecting-website/deploy-local-simple.sh
   ```

### 3. Access Your Application

The application will be available at:
- `http://YOUR-SERVER-IP` (port 80)
- Example: `http://192.168.1.100`

## 📁 File Structure

```
/opt/collecting-website/          # Application root
├── app/                          # Flask application
├── venv/                         # Python virtual environment
├── games.db                      # Database (auto-downloaded from S3)
├── .env                         # Environment variables
├── app.py                       # Main application entry point
├── collecting-website.service   # Systemd service file
└── deploy-local-simple.sh       # Simple deployment script
```

## 🔧 Service Management

### Main Application Service

```bash
# Start/stop/restart the app
sudo systemctl start collecting-website
sudo systemctl stop collecting-website
sudo systemctl restart collecting-website

# View logs
sudo journalctl -u collecting-website -f

# Check status
sudo systemctl status collecting-website
```

### Nginx

```bash
# Restart Nginx
sudo systemctl restart nginx

# Test configuration
sudo nginx -t

# View access logs
sudo tail -f /var/log/nginx/access.log
```

## 🛠 Manual Deployment

To manually deploy updates:

```bash
sudo /opt/collecting-website/deploy-local-simple.sh
```

This script will:
1. Stop the service
2. Download updated games.db from S3 (if AWS configured)
3. Install/update Python dependencies
4. Restart the application service
5. Display the local IP address for access

## 🔍 Troubleshooting

### Check Application Logs
```bash
sudo journalctl -u collecting-website -f
```

### Check Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Test Services
```bash
# Test main app directly
curl http://localhost:8080

# Test through Nginx
curl http://localhost

# Check which IP addresses are available
hostname -I
```

### Common Issues

1. **Permission errors**: Check that files are owned by `www-data`
   ```bash
   sudo chown -R www-data:www-data /opt/collecting-website
   ```

2. **Port conflicts**: Make sure port 8080 isn't in use
   ```bash
   sudo netstat -tlnp | grep :8080
   ```

3. **Database missing**: Ensure AWS credentials are configured
   ```bash
   aws configure  # Set up your AWS credentials
   ```

4. **Can't access from other devices**: Check firewall settings
   ```bash
   sudo ufw status
   sudo ufw allow from 192.168.0.0/16 to any port 80  # Allow local network
   ```

## 🔒 Security Notes

- The application runs on your local network only
- UFW firewall allows SSH, HTTP (80), and HTTPS (443)
- Service runs as non-root user (`www-data`)
- No external internet access required for the application

## 📊 Monitoring

### Check disk space
```bash
df -h
```

### Check memory usage
```bash
free -h
```

### Check running processes
```bash
ps aux | grep collecting
```

## 🆙 Updates

### Manual Code Updates

If you make changes to your code:

1. **Copy updated files to server**:
   ```bash
   sudo cp -r /path/to/updated/files/* /opt/collecting-website/
   ```

2. **Run deployment script**:
   ```bash
   sudo /opt/collecting-website/deploy-local-simple.sh
   ```

### Updating from GitHub

If you want to pull updates from GitHub:

1. **Update the repo**:
   ```bash
   cd /opt/collecting-website
   sudo -u www-data git pull origin main
   ```

2. **Run deployment script**:
   ```bash
   sudo /opt/collecting-website/deploy-local-simple.sh
   ```

## 🌐 Network Access

### Find Your Server's IP Address
```bash
hostname -I
```

### Access from Other Devices

Make sure other devices on your network can reach the server:

1. **Check firewall allows local network**:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 80
   # Adjust IP range based on your local network
   ```

2. **Test connectivity from another device**:
   ```bash
   ping YOUR-SERVER-IP
   curl http://YOUR-SERVER-IP
   ```

## 🎯 Local Network Optimization

Since this is local-only, you can:

1. **Disable HTTPS redirect** (already done in nginx config)
2. **Access via IP or set up local DNS**
3. **Use any local hostname you prefer**

To use a custom local hostname, add to `/etc/hosts` on client devices:
```
192.168.1.100 collecting.local
```

Then access via `http://collecting.local`
