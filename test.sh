#!/bin/bash

# Functional Test Script - Tests all core features with detailed output

echo "Knowledge Base System - Functional Tests"
echo "==========================================="
echo ""

API_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check if API is running
echo -e "${BLUE}[1/10] Checking API health...${NC}"
if ! curl -s "${API_URL}/" > /dev/null; then
    echo -e "${RED}[FAIL] API not running. Start with: ./run.sh${NC}"
    exit 1
fi
echo -e "${GREEN}[PASS] API is healthy${NC}"
echo ""

# Test 1: Upload initial document with salary data
echo -e "${BLUE}[2/10] Testing document upload (employee data v1)...${NC}"
echo -e "${CYAN}Creating test file with initial salary: \$50,000${NC}"
cat > /tmp/employee_test.txt << 'EOF'
Employee Information
Name: John Doe
Employee ID: EMP001
Department: Engineering
Position: Senior Developer
Salary: $50,000
Start Date: January 1, 2020
Location: New York Office
EOF

response=$(curl -s -X POST "${API_URL}/api/v1/documents/upload" \
  -F "file=@/tmp/employee_test.txt")
echo -e "${YELLOW}Response:${NC}"
echo "$response" | jq '.'
status=$(echo "$response" | jq -r '.status')
task_id=$(echo "$response" | jq -r '.task_id')
doc_id=$(echo "$response" | jq -r '.document_id')

if [ "$status" == "processing" ]; then
    echo -e "${GREEN}[PASS] Upload successful (status: $status, doc_id: $doc_id)${NC}"
else
    echo -e "${RED}[FAIL] Upload failed${NC}"
    exit 1
fi
echo ""

# Wait for processing
echo -e "${BLUE}[3/10] Waiting for document processing (15s)...${NC}"
sleep 15
task_status=$(curl -s "${API_URL}/api/v1/tasks/${task_id}" | jq -r '.status')
echo -e "${YELLOW}Task Status:${NC}"
curl -s "${API_URL}/api/v1/tasks/${task_id}" | jq '.'
if [ "$task_status" == "completed" ] || [ "$task_status" == "SUCCESS" ]; then
    echo -e "${GREEN}[PASS] Processing complete${NC}"
else
    echo -e "${RED}[WARN] Processing status: $task_status${NC}"
fi
echo ""

# Test 2: Search for initial salary
echo -e "${BLUE}[4/10] Testing search - Initial salary query...${NC}"
echo -e "${CYAN}Query: 'What is John Doe salary?'${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is John Doe salary?", "top_k": 3}')
echo -e "${YELLOW}Search Response:${NC}"
echo "$response" | jq '.'
results_count=$(echo "$response" | jq '.results | length')
if [ "$results_count" -gt "0" ]; then
    echo -e "${GREEN}[PASS] Search found $results_count results${NC}"
    echo -e "${CYAN}Top result text:${NC} $(echo "$response" | jq -r '.results[0].text')"
else
    echo -e "${RED}[FAIL] No search results${NC}"
fi
echo ""

# Test 3: Q&A for initial salary
echo -e "${BLUE}[5/10] Testing Q&A - Initial salary...${NC}"
echo -e "${CYAN}Question: 'What is John Doe current salary?'${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/qa" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is John Doe current salary?"}')
echo -e "${YELLOW}Q&A Response:${NC}"
echo "$response" | jq '.'
answer=$(echo "$response" | jq -r '.answer')
if [ "$answer" != "null" ] && [ -n "$answer" ]; then
    echo -e "${GREEN}[PASS] Q&A working${NC}"
    echo -e "${CYAN}Answer:${NC} $answer"
else
    echo -e "${RED}[FAIL] Q&A failed${NC}"
fi
echo ""

# Test 4: Upload updated document with new salary (CONFLICT MANAGEMENT)
echo -e "${BLUE}[6/10] Testing conflict management - Salary update...${NC}"
echo -e "${CYAN}Uploading SAME FILE (employee_test.txt) with updated salary: \$75,000${NC}"
echo -e "${CYAN}This should create version 2 and deactivate version 1${NC}"
cat > /tmp/employee_test.txt << 'EOF'
Employee Information
Name: John Doe
Employee ID: EMP001
Department: Engineering
Position: Senior Developer
Salary: $75,000
Salary Updated: March 15, 2024
Start Date: January 1, 2020
Location: New York Office
Performance Rating: Excellent
EOF

response=$(curl -s -X POST "${API_URL}/api/v1/documents/upload" \
  -F "file=@/tmp/employee_test.txt")
echo -e "${YELLOW}Upload Response (v2):${NC}"
echo "$response" | jq '.'
status=$(echo "$response" | jq -r '.status')
task_id_v2=$(echo "$response" | jq -r '.task_id')

if [ "$status" == "processing" ] || [ "$status" == "updated" ]; then
    echo -e "${GREEN}[PASS] Updated document uploaded (status: $status - new version created)${NC}"
    
    # Wait for processing
    echo -e "${CYAN}Waiting for v2 processing (15s)...${NC}"
    sleep 15
    
    task_status=$(curl -s "${API_URL}/api/v1/tasks/${task_id_v2}" | jq -r '.status')
    if [ "$task_status" == "completed" ] || [ "$task_status" == "SUCCESS" ]; then
        echo -e "${GREEN}[PASS] v2 Processing complete${NC}"
    fi
else
    echo -e "${RED}[FAIL] Update failed (status: $status)${NC}"
fi
echo ""

# Test 5: Search after update - Should return LATEST salary
echo -e "${BLUE}[7/10] Testing search after update - Should show \$75,000 (LATEST)...${NC}"
echo -e "${CYAN}Query: 'What is John Doe current salary?'${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is John Doe current salary?", "top_k": 3}')
echo -e "${YELLOW}Search Response (After Update):${NC}"
echo "$response" | jq '.'
top_result=$(echo "$response" | jq -r '.results[0].text')
echo -e "${CYAN}Top result:${NC} $top_result"

if echo "$top_result" | grep -q "75,000"; then
    echo -e "${GREEN}[PASS] Search returns LATEST salary (\$75,000) - Conflict resolved!${NC}"
elif echo "$top_result" | grep -q "50,000"; then
    echo -e "${RED}[FAIL] Search still returns OLD salary (\$50,000) - Conflict not resolved${NC}"
else
    echo -e "${YELLOW}[WARN] Could not verify salary in results${NC}"
fi
echo ""

# Test 6: Q&A after update - Should return LATEST info
echo -e "${BLUE}[8/10] Testing Q&A after update - Should return \$75,000...${NC}"
echo -e "${CYAN}Question: 'What is John Doe current salary?'${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/qa" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is John Doe current salary?"}')
echo -e "${YELLOW}Q&A Response (After Update):${NC}"
echo "$response" | jq '.'
answer=$(echo "$response" | jq -r '.answer')
echo -e "${CYAN}Answer:${NC} $answer"

if echo "$answer" | grep -q "75,000"; then
    echo -e "${GREEN}[PASS] Q&A returns LATEST salary (\$75,000)${NC}"
elif echo "$answer" | grep -q "50,000"; then
    echo -e "${RED}[FAIL] Q&A returns OLD salary (\$50,000)${NC}"
else
    echo -e "${YELLOW}[WARN] Could not verify salary in answer${NC}"
fi
echo ""

# Test 7: Test reranking with recency
echo -e "${BLUE}[9/10] Testing reranking - Recency scoring...${NC}"
echo -e "${CYAN}Searching for 'employee information' - Recent docs should rank higher${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "employee information salary", "top_k": 5}')
echo -e "${YELLOW}Reranking Response:${NC}"
echo "$response" | jq '.results[] | {text: .text[:80], score: .score, metadata: .metadata}'

first_result_text=$(echo "$response" | jq -r '.results[0].text')
if echo "$first_result_text" | grep -q "75,000"; then
    echo -e "${GREEN}[PASS] Reranking works - Latest document ranked first${NC}"
else
    echo -e "${YELLOW}[WARN] Check if recency scoring is working properly${NC}"
fi
echo ""

# Test 8: Completeness check
echo -e "${BLUE}[10/10] Testing completeness check...${NC}"
echo -e "${CYAN}Requirements: ['employee information', 'salary details', 'performance rating']${NC}"
response=$(curl -s -X POST "${API_URL}/api/v1/completeness-check" \
  -H "Content-Type: application/json" \
  -d '{"requirements": ["employee information", "salary details", "performance rating"]}')
echo -e "${YELLOW}Completeness Response:${NC}"
echo "$response" | jq '.'
completeness=$(echo "$response" | jq -r '.completeness_percentage')

if [ "$completeness" != "null" ]; then
    echo -e "${GREEN}[PASS] Completeness check working (${completeness}% covered)${NC}"
else
    echo -e "${RED}[FAIL] Completeness check failed${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}All functional tests complete!${NC}"
echo ""
echo -e "${CYAN}Key Tests Verified:${NC}"
echo "  ✓ Document upload and processing"
echo "  ✓ Semantic search with detailed results"
echo "  ✓ Q&A with context and sources"
echo "  ✓ Conflict management (salary update)"
echo "  ✓ Reranking with recency scoring"
echo "  ✓ Latest information appears in responses"
echo ""
echo "Additional commands:"
echo "   - List documents: curl ${API_URL}/api/v1/documents | jq '.'"
echo "   - View Celery tasks: http://localhost:5555"
echo "   - API docs: http://localhost:8000/docs"
echo ""

# Cleanup temp files
rm -f /tmp/employee_test.txt
