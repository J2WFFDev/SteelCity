# Jims Test Commands

Check if a Bridge is running
ssh jrwest@192.168.1.173 'ps aux | grep "bridge" | grep -v grep || true'

Kill Bridge Processes
ssh jrwest@192.168.1.173 'pkill -f "continuous_bridge.py" || pkill -f "minimal_bridge.py" || pkill -f "bridge.py" || true'

Minimum Bridge
ssh jrwest@192.168.1.173 'cd ~/projects/steelcity && timeout 30 .venv/bin/python minimal_bridge.py'

Production
ssh jrwest@192.168.1.173 'cd ~/projects/steelcity && timeout 30 .venv/bin/python bridge.py'
