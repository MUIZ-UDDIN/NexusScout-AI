@echo off
REM Starts localtunnel for the NexusScout backend (port 8001)
REM URL stays the same: https://nexus-scout-backend.loca.lt
REM Keep this window open. Close it to stop the tunnel.
npx localtunnel --port 8001 --subdomain nexus-scout-backend
