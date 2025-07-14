import openai
import cv2
import base64
import os
import time
import threading
import ast
import re

# ========== CONFIG ==========
openai.api_key = "KEY"
WEBCAM_INDEX = 0
IMAGE_PATH = "image.png"
DICT_PATH = "dictionary.txt"
INSTRUCTIONS_PATH = "instructions.txt"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ========== IMAGE CAPTURE ==========
def capture_image(path=IMAGE_PATH, index=0, width=1280, height=720):
    print("📸 Capturing image from webcam...")
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    time.sleep(1)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("❌ Could not capture image from webcam.")
    cv2.imwrite(path, frame)
    print(f"✅ Image saved to '{path}'.")

# ========== IMAGE TO BASE64 ==========
def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ========== EXTRACT PYTHON CODE BLOCK ==========
def extract_code_block(text):
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

# ========== GET GRID FROM OPENAI ==========
def get_grid_from_image(base64_image):
    prompt = (
        "This is a 4x4 grid of English uppercase letters. "
        "Return ONLY the grid as a Python 2D list (4 rows, 4 letters per row). "
        "NO explanation, no extra text."
    )

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You're a helpful assistant."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ],
        max_tokens=150,
    )

    content = response.choices[0].message.content
    code_str = extract_code_block(content)

    try:
        grid = ast.literal_eval(code_str)
        if not (isinstance(grid, list) and len(grid) == 4 and all(isinstance(row, list) and len(row) == 4 for row in grid)):
            raise ValueError("Parsed grid is not valid 4x4.")
        return grid
    except Exception:
        raise ValueError(f"❌ Couldn't parse OpenAI's grid output. Raw output:\n{content}")

# ========== TRIE FOR DICTIONARY ==========
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for c in word:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
        node.is_word = True

    def starts_with(self, prefix):
        node = self.root
        for c in prefix:
            if c not in node.children:
                return None
            node = node.children[c]
        return node

# ========== LOAD DICTIONARY ==========
def load_dictionary(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dictionary file '{path}' not found.")
    with open(path, 'r') as f:
        return set(word.strip().upper() for word in f if len(word.strip()) >= 3)

# ========== DFS WORD FINDER ==========
def find_words(grid, dictionary):
    trie = Trie()
    for word in dictionary:
        trie.insert(word)

    rows, cols = 4, 4
    found = {}
    lock = threading.Lock()

    def dfs(r, c, node, prefix, visited, path):
        if (r < 0 or r >= rows or c < 0 or c >= cols or (r, c) in visited):
            return
        letter = grid[r][c]
        if letter not in node.children:
            return

        visited.add((r, c))
        path.append((r, c))
        node = node.children[letter]
        word = prefix + letter

        if node.is_word and len(word) >= 3:
            with lock:
                if word not in found:
                    found[word] = list(path)

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr != 0 or dc != 0:
                    dfs(r + dr, c + dc, node, word, visited, path)

        visited.remove((r, c))
        path.pop()

    threads = []
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] in trie.root.children:
                t = threading.Thread(target=dfs, args=(i, j, trie.root, "", set(), []))
                t.start()
                threads.append(t)

    for t in threads:
        t.join()

    return sorted(found.items(), key=lambda x: len(x[0]), reverse=True)

# ========== MAIN ==========
def main():
    try:
        capture_image()
        b64 = encode_image(IMAGE_PATH)
        grid = get_grid_from_image(b64)

        print("\n🧩 Recognized Grid:")
        for row in grid:
            print(" ".join(row))

        dictionary = load_dictionary(DICT_PATH)
        words_with_paths = find_words(grid, dictionary)

        print("\n📜 Words Found (longest to shortest):")
        output_array = []

        for word, path in words_with_paths:
            # Flip row index to make (0,0) bottom-left and (3,3) top-right
            flipped_path = [(3 - r, c) for r, c in path]
            path_str = "->".join(f"({r},{c})" for r, c in flipped_path)
            print(f"{word}: {path_str}")

            output_array.append("DOWN")
            for r, c in flipped_path:
                output_array.append(f"{r},{c}")
            output_array.append("UP")

        print("\n🖲️ Stylus Command Array:")
        print(output_array)

        # Write to instructions.txt
        with open(INSTRUCTIONS_PATH, "w") as f:
            f.write(str(output_array))
        print(f"\n💾 Saved instructions to '{INSTRUCTIONS_PATH}'.")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
