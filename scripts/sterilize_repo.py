import os
import re

target_dir = r"c:\Users\kaiba\.gemini\antigravity\scratch\neurovynx_github"

# 1. Regex patterns for sterilization
patterns = [
    # Personal Machine Paths
    (re.compile(r'C:\\Users\\kaiba\\[^\s"\')]*', re.IGNORECASE), "[LOCAL_PATH_REMOVED]"),
    
    # Debug Residue (Basic prints and console logs)
    # We target prints that look like debug spam (simple strings)
    (re.compile(r'print\(\s*["\'](DEBUG|HERE|got|data|test|check).*["\']\s*\)', re.IGNORECASE), "# Cleaned debug log"),
    (re.compile(r'console\.log\(\s*["\'](DEBUG|HERE|got|data|test|check).*["\']\s*\)', re.IGNORECASE), "// Cleaned debug log"),
    
    # Internal Usernames / References (Be careful with Cff/License)
    # We avoid the CITATION.cff and LICENSE files for this rule
    (re.compile(r'kaiba|gemini', re.IGNORECASE), "neurovynx_ref") 
]

# Files to exclude from name scrubbing (to preserve proper citations)
protected_files = ["CITATION.cff", "LICENSE", "README.md", "walkthrough.md"]

def sterilize_file(filepath):
    # Only process text files
    if not any(filepath.endswith(ext) for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".bat", ".sh", ".yml"]):
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    new_content = content
    filename = os.path.basename(filepath)

    # Apply general scrubs
    new_content = re.sub(r'C:\\Users\\kaiba\\[^\s"\')]*', "[LOCAL_PATH]", new_content, flags=re.IGNORECASE)
    
    # Apply name scrubs if not protected
    if filename not in protected_files:
        new_content = re.sub(r'kaiba', "neurovynx_dev", new_content, flags=re.IGNORECASE)
        new_content = re.sub(r'gemini', "context_ai", new_content, flags=re.IGNORECASE)

    # Normalize Endpoints
    new_content = re.sub(r'http://localhost:\d+', "http://localhost:8000", new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

# Execution
count = 0
for root, dirs, files in os.walk(target_dir):
    # Skip .venv and node_modules
    if ".venv" in root or "node_modules" in root:
        continue
    for file in files:
        if sterilize_file(os.path.join(root, file)):
            count += 1

print(f"Sterilization complete. {count} files sanitized.")
