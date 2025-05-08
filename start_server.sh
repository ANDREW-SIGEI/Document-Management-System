#!/bin/bash

# Colors for better visibility
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== KEMRI Laboratory System Server Startup ===${NC}"

# Kill any existing Flask processes
echo -e "${YELLOW}Stopping any running Flask servers...${NC}"
pkill -f "python run_*.py" || true
fuser -k 5000/tcp || true
fuser -k 5001/tcp || true
fuser -k 8080/tcp || true
fuser -k 3000/tcp || true  # Added to kill port 3000 too

# Check database issues
echo -e "${YELLOW}Checking database schema...${NC}"
python add_is_active_column.py

# Ask if user wants to generate sample data
echo -e "${YELLOW}Would you like to generate sample data for the presentation? (y/n)${NC}"
read -r generate_data

if [[ "$generate_data" == "y" || "$generate_data" == "Y" ]]; then
    echo -e "${YELLOW}Generating sample data...${NC}"
    python generate_sample_data.py
    echo -e "${GREEN}Sample data generated successfully.${NC}"
fi

# Database should be good now, run the server
echo -e "${GREEN}Starting the server in debug mode on port 3000...${NC}"
echo -e "${YELLOW}(This is the recommended mode for presentation)${NC}"
echo ""
echo -e "${GREEN}The application will be available at:${NC}"
echo -e "${YELLOW}http://127.0.0.1:3000${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Open browser automatically
xdg-open http://127.0.0.1:3000 &

# Run the app directly on port 3000
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=3000

# If we get here, the server was stopped
echo -e "${RED}Server stopped.${NC}" 