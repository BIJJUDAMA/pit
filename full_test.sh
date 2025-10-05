set -e

echo "---"
echo "--- Starting Full Test ---"
echo "---"

# === 1. DOCKER CLEANUP AND REBUILD ===
echo -e "\n[STEP 1] Cleaning up previous Docker containers and images..."

# Stop and remove any containers created from the 'pit-env' image.
# The '|| true' prevents the script from failing if no containers are found.
docker rm -f $(docker ps -aq --filter "ancestor=pit-env") || true

# Remove the old 'pit-env' image.
docker rmi pit-env || true

echo "[SUCCESS] Docker cleanup complete."

echo -e "\n[STEP 2] Building a fresh Docker image from scratch..."
# Build the image with --no-cache to ensure all latest file changes are included.
docker build --no-cache -t pit-env .
echo "[SUCCESS] New 'pit-env' image built."


# === 2. EXECUTE TEST SUITE INSIDE THE NEW CONTAINER ===
echo -e "\n[STEP 3] Running the comprehensive test suite inside a new container..."

# Use a 'here document' (<<EOF) to pass the entire test script into the container.
# The container will start, create a test directory, and run all the commands inside it.
docker run -i --rm -v "$(pwd)":/workspace pit-env /bin/bash <<'EOF'
set -e

echo "--- Now running inside the container ---"

# Create a clean directory for this test run
rm -rf pit-full-test
mkdir pit-full-test
cd pit-full-test

echo -e "\n[TEST 1] Initializing repository and setting user config..."
pit init
pit config user.name "Test User"
pit config user.email "test@example.com"
echo "[SUCCESS] Repository initialized and user configured."

echo -e "\n[TEST 2] Creating initial file structure and making first commit..."
mkdir -p src/utils
echo "*.log" > .pitignore
echo "build/" >> .pitignore
echo "Initial content for file1" > file1.txt
echo "def main():\n    print('hello world')" > src/main.py
echo "helper function" > src/utils/helpers.py
pit add .
pit commit -m "Initial commit: Add project structure with multiple directories"
echo "[SUCCESS] First commit created."
echo -e "\n--- Verifying log history ---"
pit log

echo -e "\n[TEST 3] Testing branching and feature development..."
pit branch feature-A
pit checkout feature-A
echo "New feature content" > feature.txt
pit add feature.txt
pit commit -m "Add new feature file on feature-A branch"
echo "[SUCCESS] Committed new feature on branch 'feature-A'."
echo -e "\n--- Verifying log history on feature-A ---"
pit log

echo -e "\n[TEST 4] Making a separate change on the master branch..."
pit checkout master
echo "def main():\n    print('hello world from master branch')" > src/main.py
pit add src/main.py
pit commit -m "Update main.py on master branch"
echo "[SUCCESS] Committed change on master."
echo -e "\n--- Verifying log history on master ---"
pit log

echo -e "\n[TEST 5] Testing 'diff' and 'reset' commands..."
pit checkout feature-A
echo "More feature work" >> feature.txt
echo "An unstaged change in file1" >> file1.txt
pit add feature.txt
echo -e "\n--- Verifying 'pit diff --staged' ---"
pit diff --staged
pit reset feature.txt
echo -e "\n--- Verifying 'pit status' after reset ---"
pit status
echo "[SUCCESS] Diff and reset commands are working correctly."

echo -e "\n[TEST 6] Testing merge functionality..."
pit checkout master
pit merge feature-A
echo "[SUCCESS] Merge command executed."
echo -e "\n--- Verifying log history after merge ---"
pit log
echo "[SUCCESS] Combined history is correct."
echo -e "\n--- Verifying file state after merge ---"
if [ -f "feature.txt" ] && grep -q "master branch" src/main.py; then
    echo "[SUCCESS] Files are in the correct state after merge."
else
    echo "[FAILURE] File state is incorrect after merge."
    exit 1
fi
EOF

echo -e "\n---"
echo "--- Test Completed Successfully! ---"
echo "---"
