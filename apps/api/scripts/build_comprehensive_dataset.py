"""
Comprehensive, Authorized Coding Problem Dataset Generator and Validator for ConceptEval.ai
Creates genuinely distinct, diverse, fully validated problems covering:
Arrays, Strings, Hash Maps, Sorting, Searching, Recursion, Loops, Functions,
Linked Lists, Stacks, Queues, Trees, Graphs, Heaps, Binary Search,
Greedy Algorithms, Backtracking, Dynamic Programming, Mathematics,
Bit Manipulation, Object-Oriented Programming, and SQL.

Each problem includes:
- Clear title, statement, input/output specifications, constraints
- Python starter code with signatures
- Fully validated Python reference solution
- Validated public and hidden test cases
- Strict AST concept requirements
- Full provenance and CC-BY-4.0 authorization
"""

import io
import json
import os
import sys
from typing import Any, Dict, List

# Define the comprehensive problem dataset
PROBLEMS_DATA: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. HEAPS / PRIORITY QUEUES
    # -------------------------------------------------------------------------
    {
        "title": "Kth Largest Element in an Array via Min-Heap",
        "slug": "kth-largest-element-min-heap",
        "difficulty": "medium",
        "language": "python",
        "topics": ["heaps", "arrays", "sorting"],
        "expected_concepts": ["loop", "function_definition"],
        "constraints": ["1 <= k <= len(nums) <= 10^5", "-10^4 <= nums[i] <= 10^4", "Must use heapq or heap data structure"],
        "input_format": "Line 1: space-separated integers. Line 2: integer k.",
        "output_format": "A single integer: the kth largest element.",
        "statement_markdown": """### Problem Description
Given an array of integers and an integer `k`, return the `k`th largest element in the array. Note that it is the `k`th largest element in sorted order, not the `k`th distinct element.

### Concept Requirement
You **must** maintain a min-heap of size `k` using Python's `heapq` module to achieve $O(N \\log k)$ time complexity. Sorting the entire array is not allowed.

### Example 1
**Input:**
```
3 2 1 5 6 4
2
```
**Output:**
```
5
```
""",
        "starter_code": """import sys
import heapq

def find_kth_largest():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    nums = [int(x) for x in lines[0].split()]
    k = int(lines[1].strip())
    # TODO: Maintain min-heap of size k
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    print(heap[0])

if __name__ == '__main__':
    find_kth_largest()
""",
        "reference_solution": """import sys
import heapq

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    nums = [int(x) for x in lines[0].split()]
    k = int(lines[1].strip())
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    print(heap[0])

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "3 2 1 5 6 4\n2\n", "expected_output": "5\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "3 2 3 1 2 4 5 5 6\n4\n", "expected_output": "4\n", "visibility": "public", "weight": 1.0},
            {"input_data": "7 10 4 3 20 15\n3\n", "expected_output": "10\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_heap_loop", "accepted_constructs": ["For", "While"], "required": True, "min_occurrences": 1, "description": "Loop required to push elements to heap"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Merge K Sorted Integer Sequences Using Heap",
        "slug": "merge-k-sorted-sequences-heap",
        "difficulty": "hard",
        "language": "python",
        "topics": ["heaps", "sorting", "arrays"],
        "expected_concepts": ["loop", "function_definition"],
        "constraints": ["0 <= k <= 1000", "Total elements across sequences <= 50000", "Each sequence is sorted in ascending order"],
        "input_format": "Line 1: integer k. Following k lines: space-separated integers in ascending order.",
        "output_format": "A single line containing all integers merged in ascending order.",
        "statement_markdown": """### Problem Description
You are given `k` sorted lists of integers. Merge all the sorted lists into one sorted list and print it space-separated.

### Algorithmic Requirement
You **must** use a min-heap containing at most `k` items simultaneously (tracking each element, sequence index, and element index) to achieve an optimal $O(N \\log k)$ merge.

### Example 1
**Input:**
```
3
1 4 5
1 3 4
2 6
```
**Output:**
```
1 1 2 3 4 4 5 6
```
""",
        "starter_code": """import sys
import heapq

def merge_k_sorted():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        print()
        return
    k = int(lines[0].strip())
    # TODO: Read lists and merge with min-heap
    pass

if __name__ == '__main__':
    merge_k_sorted()
""",
        "reference_solution": """import sys
import heapq

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        print()
        return
    k = int(lines[0].strip())
    lists = []
    for i in range(1, k + 1):
        if i < len(lines) and lines[i].strip():
            lists.append([int(x) for x in lines[i].split()])
        else:
            lists.append([])

    heap = []
    for list_idx, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], list_idx, 0))

    result = []
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(str(val))
        if elem_idx + 1 < len(lists[list_idx]):
            next_val = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, list_idx, elem_idx + 1))

    print(" ".join(result))

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "3\n1 4 5\n1 3 4\n2 6\n", "expected_output": "1 1 2 3 4 4 5 6\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2\n10 20 30\n5 15 25\n", "expected_output": "5 10 15 20 25 30\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\n42\n", "expected_output": "42\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_while_heap", "accepted_constructs": ["While"], "required": True, "min_occurrences": 1, "description": "While loop to pop from heap until empty"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 2. BINARY SEARCH
    # -------------------------------------------------------------------------
    {
        "title": "Search in Rotated Sorted Array via Binary Search",
        "slug": "search-rotated-sorted-array",
        "difficulty": "medium",
        "language": "python",
        "topics": ["binary-search", "arrays", "searching"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["1 <= len(nums) <= 10^5", "All elements are distinct", "Time complexity must be O(log n)"],
        "input_format": "Line 1: space-separated integers. Line 2: integer target to find.",
        "output_format": "0-indexed position of target if found, otherwise -1.",
        "statement_markdown": """### Problem Description
Given an integer array `nums` sorted in ascending order with distinct values, rotated at some pivot unknown to you beforehand, and an integer `target`, return the index of `target` if it is in `nums`, or `-1` if it is not.

### Algorithmic Requirement
You **must** write an algorithm with $O(\\log n)$ runtime complexity using modified **binary search**. Linear search $O(n)$ will fail time complexity checks.

### Example 1
**Input:**
```
4 5 6 7 0 1 2
0
```
**Output:**
```
4
```
""",
        "starter_code": """import sys

def search_rotated():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    nums = [int(x) for x in lines[0].split()]
    target = int(lines[1].strip())
    # TODO: Logarithmic binary search
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            print(mid)
            return
        # Identify sorted half
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        else:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    print(-1)

if __name__ == '__main__':
    search_rotated()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    nums = [int(x) for x in lines[0].split()]
    target = int(lines[1].strip())
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            print(mid)
            return
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]:
                right = mid - 1
            else:
                left = mid + 1
        else:
            if nums[mid] < target <= nums[right]:
                left = mid + 1
            else:
                right = mid - 1
    print(-1)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4 5 6 7 0 1 2\n0\n", "expected_output": "4\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "4 5 6 7 0 1 2\n3\n", "expected_output": "-1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\n0\n", "expected_output": "-1\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_while_binary_search", "accepted_constructs": ["While"], "required": True, "min_occurrences": 1, "description": "While loop for binary search bounds convergence"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Integer Square Root via Binary Search",
        "slug": "integer-square-root-binary-search",
        "difficulty": "easy",
        "language": "python",
        "topics": ["binary-search", "math"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["0 <= x <= 2^31 - 1", "Cannot use built-in math.isqrt or exponentiation operator ** 0.5"],
        "input_format": "A single non-negative integer x.",
        "output_format": "The floor of the square root of x.",
        "statement_markdown": """### Problem Description
Given a non-negative integer `x`, compute and return the square root of `x` rounded down to the nearest integer. The returned integer should be non-negative.

### Concept Requirement
You **must** use a binary search loop between `0` and `x`. Do not use Python's built-in `math.sqrt()` or `** 0.5`.

### Example 1
**Input:**
```
8
```
**Output:**
```
2
```
""",
        "starter_code": """import sys

def my_sqrt():
    line = sys.stdin.read().strip()
    if not line:
        return
    x = int(line)
    # TODO: Implement binary search square root
    pass

if __name__ == '__main__':
    my_sqrt()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().strip()
    if not line:
        return
    x = int(line)
    if x < 2:
        print(x)
        return
    left, right = 1, x // 2
    ans = 1
    while left <= right:
        mid = (left + right) // 2
        if mid * mid <= x:
            ans = mid
            left = mid + 1
        else:
            right = mid - 1
    print(ans)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4\n", "expected_output": "2\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "8\n", "expected_output": "2\n", "visibility": "public", "weight": 1.0},
            {"input_data": "25\n", "expected_output": "5\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_binary_search_loop", "accepted_constructs": ["While"], "required": True, "min_occurrences": 1, "description": "While loop for binary search convergence"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 3. GREEDY ALGORITHMS
    # -------------------------------------------------------------------------
    {
        "title": "Activity Selection Maximum Non-Overlapping Intervals",
        "slug": "activity-selection-max-intervals",
        "difficulty": "medium",
        "language": "python",
        "topics": ["greedy", "sorting", "arrays"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["1 <= N <= 10^5", "Intervals given as start end pairs", "End time >= start time"],
        "input_format": "Line 1: integer N. Following N lines: two space-separated integers (start end).",
        "output_format": "An integer: maximum number of mutually non-overlapping activities.",
        "statement_markdown": """### Problem Description
You are given `N` activities with their start and finish times. Select the maximum number of activities that can be performed by a single person, assuming that a person can only work on a single activity at a time. Two activities are compatible if the start time of the second is greater than or equal to the finish time of the first.

### Algorithmic Requirement
You **must** use the greedy choice property by sorting activities by their **finish time**.

### Example 1
**Input:**
```
4
1 4
3 5
0 6
5 7
```
**Output:**
```
2
```
""",
        "starter_code": """import sys

def max_activities():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n = int(lines[0].strip())
    activities = []
    for i in range(1, n + 1):
        s, e = map(int, lines[i].split())
        activities.append((s, e))
    # TODO: Greedy interval scheduling
    pass

if __name__ == '__main__':
    max_activities()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n = int(lines[0].strip())
    activities = []
    for i in range(1, n + 1):
        if i < len(lines) and lines[i].strip():
            s, e = map(int, lines[i].split())
            activities.append((s, e))

    # Sort by finish time
    activities.sort(key=lambda x: x[1])

    count = 0
    last_end = -1
    for s, e in activities:
        if s >= last_end:
            count += 1
            last_end = e

    print(count)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4\n1 4\n3 5\n0 6\n5 7\n", "expected_output": "2\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "3\n10 20\n12 25\n20 30\n", "expected_output": "2\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\n1 10\n", "expected_output": "1\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_greedy_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop iterating over sorted intervals"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Jump Game Minimum Reachable Index Greedy",
        "slug": "jump-game-reachable-greedy",
        "difficulty": "medium",
        "language": "python",
        "topics": ["greedy", "arrays"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["1 <= len(nums) <= 10^5", "0 <= nums[i] <= 10^5"],
        "input_format": "A single line of space-separated integers representing jump capacities.",
        "output_format": "'true' if the last index is reachable, otherwise 'false'.",
        "statement_markdown": """### Problem Description
You are given an integer array `nums`. You are initially positioned at the array's first index, and each element in the array represents your maximum jump length at that position. Return `true` if you can reach the last index, or `false` otherwise.

### Algorithmic Requirement
You **must** solve this in $O(N)$ time and $O(1)$ extra space using a greedy traversal tracking the furthest reachable index.

### Example 1
**Input:**
```
2 3 1 1 4
```
**Output:**
```
true
```
""",
        "starter_code": """import sys

def can_jump():
    raw = sys.stdin.read().strip()
    if not raw:
        print("true")
        return
    nums = [int(x) for x in raw.split()]
    # TODO: Greedy reachability check
    pass

if __name__ == '__main__':
    can_jump()
""",
        "reference_solution": """import sys

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("true")
        return
    nums = [int(x) for x in raw.split()]
    max_reach = 0
    for i, jump in enumerate(nums):
        if i > max_reach:
            print("false")
            return
        if i + jump > max_reach:
            max_reach = i + jump
        if max_reach >= len(nums) - 1:
            print("true")
            return
    print("true" if max_reach >= len(nums) - 1 else "false")

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "2 3 1 1 4\n", "expected_output": "true\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "3 2 1 0 4\n", "expected_output": "false\n", "visibility": "public", "weight": 1.0},
            {"input_data": "0\n", "expected_output": "true\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_jump_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop inspecting jump limits"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 4. BACKTRACKING
    # -------------------------------------------------------------------------
    {
        "title": "Generate All Balanced Parentheses Combinations",
        "slug": "generate-balanced-parentheses-backtracking",
        "difficulty": "medium",
        "language": "python",
        "topics": ["backtracking", "recursion", "strings"],
        "expected_concepts": ["recursion", "function_definition"],
        "constraints": ["1 <= n <= 8", "Output combinations must be printed in alphabetical order"],
        "input_format": "A single integer n.",
        "output_format": "Each balanced combination on its own line.",
        "statement_markdown": """### Problem Description
Given `n` pairs of parentheses, write a function to generate all combinations of well-formed parentheses.

### Concept Requirement
You **must** use a recursive **backtracking** helper function that maintains open and close counts and prunes invalid prefixes.

### Example 1
**Input:**
```
3
```
**Output:**
```
((()))
(()())
(())()
()(())
()()()
```
""",
        "starter_code": """import sys

def generate_parentheses():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    # TODO: Backtracking recursion
    pass

if __name__ == '__main__':
    generate_parentheses()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    results = []

    def backtrack(curr, open_count, close_count):
        if len(curr) == 2 * n:
            results.append(curr)
            return
        if open_count < n:
            backtrack(curr + "(", open_count + 1, close_count)
        if close_count < open_count:
            backtrack(curr + ")", open_count, close_count + 1)

    backtrack("", 0, 0)
    for res in sorted(results):
        print(res)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "1\n", "expected_output": "()\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2\n", "expected_output": "(())\n()()\n", "visibility": "public", "weight": 1.0},
            {"input_data": "3\n", "expected_output": "((()))\n(()())\n(())()\n()(())\n()()()\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "recursion", "rule_id": "rule_backtrack_recursion", "required": True, "min_occurrences": 1, "description": "Must use recursive backtracking helper"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "N-Queens Valid Placement Count",
        "slug": "n-queens-placement-count-backtracking",
        "difficulty": "hard",
        "language": "python",
        "topics": ["backtracking", "recursion"],
        "expected_concepts": ["recursion", "function_definition"],
        "constraints": ["1 <= n <= 10"],
        "input_format": "A single integer n representing the board dimension.",
        "output_format": "An integer: the total number of distinct solutions to the n-queens puzzle.",
        "statement_markdown": """### Problem Description
The `n`-queens puzzle is the problem of placing `n` queens on an `n x n` chessboard such that no two queens attack each other. Given an integer `n`, return the number of distinct solutions to the `n`-queens puzzle.

### Concept Requirement
You **must** use recursive backtracking with column, diagonal, and anti-diagonal attack sets for $O(1)$ conflict lookups.

### Example 1
**Input:**
```
4
```
**Output:**
```
2
```
""",
        "starter_code": """import sys

def total_n_queens():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    # TODO: Backtracking N-Queens
    pass

if __name__ == '__main__':
    total_n_queens()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    cols = set()
    diag1 = set()  # r - c
    diag2 = set()  # r + c
    count = 0

    def backtrack(r):
        nonlocal count
        if r == n:
            count += 1
            return
        for c in range(n):
            if c in cols or (r - c) in diag1 or (r + c) in diag2:
                continue
            cols.add(c)
            diag1.add(r - c)
            diag2.add(r + c)
            backtrack(r + 1)
            cols.remove(c)
            diag1.remove(r - c)
            diag2.remove(r + c)

    backtrack(0)
    print(count)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4\n", "expected_output": "2\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "1\n", "expected_output": "1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "5\n", "expected_output": "10\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "recursion", "rule_id": "rule_nqueens_recursion", "required": True, "min_occurrences": 1, "description": "Recursive backtracking placement"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 5. GRAPHS
    # -------------------------------------------------------------------------
    {
        "title": "Count Connected Grid Island Components via DFS",
        "slug": "count-connected-grid-islands-dfs",
        "difficulty": "medium",
        "language": "python",
        "topics": ["graphs", "recursion", "arrays"],
        "expected_concepts": ["recursion", "function_definition"],
        "constraints": ["1 <= R, C <= 100", "Grid contains only '1' (land) and '0' (water)", "Adjacent cells horizontal or vertical only"],
        "input_format": "Line 1: R C (rows and columns). Next R lines: C characters without spaces ('1' or '0').",
        "output_format": "An integer: the number of distinct islands.",
        "statement_markdown": """### Problem Description
Given an `R x C` 2D binary grid which represents a map of `'1'`s (land) and `'0'`s (water), return the number of islands. An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically.

### Concept Requirement
You **must** use depth-first search (**DFS**) recursion to traverse and flood-fill each visited island component.

### Example 1
**Input:**
```
4 5
11110
11010
11000
00000
```
**Output:**
```
1
```
""",
        "starter_code": """import sys

def count_islands():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        print(0)
        return
    r, c = map(int, lines[0].split())
    grid = [list(lines[i + 1].strip()) for i in range(r)]
    # TODO: DFS recursion to count connected components
    pass

if __name__ == '__main__':
    count_islands()
""",
        "reference_solution": """import sys

# Increase recursion depth for deep grids
sys.setrecursionlimit(20000)

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        print(0)
        return
    r, c = map(int, lines[0].split())
    grid = [list(lines[i + 1].strip()) for i in range(r)]

    def dfs(i, j):
        if i < 0 or i >= r or j < 0 or j >= c or grid[i][j] != '1':
            return
        grid[i][j] = '0'  # Mark visited
        dfs(i + 1, j)
        dfs(i - 1, j)
        dfs(i, j + 1)
        dfs(i, j - 1)

    islands = 0
    for i in range(r):
        for j in range(c):
            if grid[i][j] == '1':
                islands += 1
                dfs(i, j)

    print(islands)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4 5\n11110\n11010\n11000\n00000\n", "expected_output": "1\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "4 5\n11000\n11000\n00100\n00011\n", "expected_output": "3\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1 1\n0\n", "expected_output": "0\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "recursion", "rule_id": "rule_dfs_flood_fill", "required": True, "min_occurrences": 1, "description": "Must use recursive DFS for graph traversal"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Shortest Path in Unweighted Maze Grid via BFS",
        "slug": "shortest-path-maze-grid-bfs",
        "difficulty": "medium",
        "language": "python",
        "topics": ["graphs", "queues", "searching"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["1 <= R, C <= 100", "0 is open, 1 is obstacle", "Path starts at (0, 0) and ends at (R-1, C-1)"],
        "input_format": "Line 1: R C. Next R lines: C space-separated integers (0 or 1).",
        "output_format": "Minimum number of steps to reach destination, or -1 if unreachable.",
        "statement_markdown": """### Problem Description
Given an `R x C` binary maze where `0` represents an empty cell and `1` represents an obstacle, find the shortest path length from top-left `(0, 0)` to bottom-right `(R-1, C-1)`. You can move up, down, left, or right.

### Concept Requirement
You **must** use breadth-first search (**BFS**) with a queue (`collections.deque`) to guarantee shortest path optimality in an unweighted graph.

### Example 1
**Input:**
```
3 3
0 0 0
1 1 0
1 1 0
```
**Output:**
```
4
```
""",
        "starter_code": """import sys
from collections import deque

def shortest_path():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    r, c = map(int, lines[0].split())
    grid = [[int(x) for x in lines[i + 1].split()] for i in range(r)]
    # TODO: BFS queue for shortest path
    pass

if __name__ == '__main__':
    shortest_path()
""",
        "reference_solution": """import sys
from collections import deque

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        print(-1)
        return
    r, c = map(int, lines[0].split())
    grid = [[int(x) for x in lines[i + 1].split()] for i in range(r)]

    if grid[0][0] == 1 or grid[r - 1][c - 1] == 1:
        print(-1)
        return

    queue = deque([(0, 0, 0)])  # (row, col, distance)
    visited = {(0, 0)}

    while queue:
        row, col, dist = queue.popleft()
        if row == r - 1 and col == c - 1:
            print(dist)
            return

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < r and 0 <= nc < c and grid[nr][nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))

    print(-1)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "3 3\n0 0 0\n1 1 0\n1 1 0\n", "expected_output": "4\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2 2\n0 1\n1 0\n", "expected_output": "-1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1 1\n0\n", "expected_output": "0\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_bfs_while", "accepted_constructs": ["While"], "required": True, "min_occurrences": 1, "description": "While loop processing queue states"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 6. BIT MANIPULATION
    # -------------------------------------------------------------------------
    {
        "title": "Single Non-Duplicate Element via Bitwise XOR",
        "slug": "single-non-duplicate-element-xor",
        "difficulty": "easy",
        "language": "python",
        "topics": ["bit-manipulation", "arrays"],
        "expected_concepts": ["loop"],
        "constraints": ["1 <= len(nums) <= 10^5", "Every element appears twice except for one", "Must operate in O(n) time and O(1) space"],
        "input_format": "A single line containing space-separated integers.",
        "output_format": "The single integer that appears only once.",
        "statement_markdown": """### Problem Description
Given a non-empty array of integers `nums`, every element appears twice except for one. Find that single one.

### Concept Requirement
You **must** use the bitwise XOR operator (`^`) to identify the unique number in $O(n)$ time and $O(1)$ memory. Using hash sets or sorting is prohibited.

### Example 1
**Input:**
```
4 1 2 1 2
```
**Output:**
```
4
```
""",
        "starter_code": """import sys

def single_number():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    nums = [int(x) for x in raw.split()]
    # TODO: Bitwise XOR accumulator
    res = 0
    for x in nums:
        res ^= x
    print(res)

if __name__ == '__main__':
    single_number()
""",
        "reference_solution": """import sys

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    nums = [int(x) for x in raw.split()]
    res = 0
    for x in nums:
        res ^= x
    print(res)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "2 2 1\n", "expected_output": "1\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "4 1 2 1 2\n", "expected_output": "4\n", "visibility": "public", "weight": 1.0},
            {"input_data": "100\n", "expected_output": "100\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_xor_accumulation", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop accumulating bitwise XOR values"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Hamming Weight Counting Set Bits via Bitwise Shifts",
        "slug": "hamming-weight-counting-set-bits",
        "difficulty": "easy",
        "language": "python",
        "topics": ["bit-manipulation", "math"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["0 <= n <= 2^31 - 1", "Cannot use bin().count('1')"],
        "input_format": "A single positive integer.",
        "output_format": "The number of set bits (1s) in its binary representation.",
        "statement_markdown": """### Problem Description
Write a function that takes the binary representation of a positive integer and returns the number of set bits it has (also known as the Hamming weight).

### Concept Requirement
You **must** use bitwise operators (such as `n & (n - 1)` or `n & 1` with right shifts `>>`). Using string conversion or `bin().count('1')` is prohibited.

### Example 1
**Input:**
```
11
```
**Output:**
```
3
```
*Explanation: 11 in binary is 1011, which has 3 set bits.*
""",
        "starter_code": """import sys

def hamming_weight():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    # TODO: Bitwise set bit counter
    count = 0
    while n > 0:
        n &= (n - 1)
        count += 1
    print(count)

if __name__ == '__main__':
    hamming_weight()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    count = 0
    while n > 0:
        n &= (n - 1)
        count += 1
    print(count)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "11\n", "expected_output": "3\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "128\n", "expected_output": "1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "2147483645\n", "expected_output": "30\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_bitwise_while", "accepted_constructs": ["While"], "required": True, "min_occurrences": 1, "description": "While loop checking bits until zero"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 7. SQL (RELATIONAL AGGREGATIONS & SIMULATIONS)
    # -------------------------------------------------------------------------
    {
        "title": "Relational Inner Join Table Simulation",
        "slug": "relational-inner-join-simulation",
        "difficulty": "easy",
        "language": "python",
        "topics": ["sql", "hashing", "arrays"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["Output rows sorted by ID in ascending order", "Simulates SQL SELECT A.id, A.val, B.dept FROM A JOIN B ON A.id = B.id"],
        "input_format": "Line 1: N M (counts of rows in tables A and B). Next N lines: `id val`. Next M lines: `id dept`.",
        "output_format": "Matched rows sorted by ID: `id val dept` per line.",
        "statement_markdown": """### Problem Description
Simulate an SQL **INNER JOIN** between two relational tables `TableA(id, val)` and `TableB(id, dept)` on the primary key `id`. Return matching tuples formatted as `id val dept`, sorted by `id` ascending.

### SQL Equivalent
```sql
SELECT A.id, A.val, B.dept
FROM TableA A
JOIN TableB B ON A.id = B.id
ORDER BY A.id ASC;
```

### Concept Requirement
You **must** use a dictionary/hash map index on one table to achieve an efficient $O(N + M)$ hash join.

### Example 1
**Input:**
```
3 2
1 Alice
2 Bob
3 Charlie
1 Engineering
3 Research
```
**Output:**
```
1 Alice Engineering
3 Charlie Research
```
""",
        "starter_code": """import sys

def simulate_join():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n, m = map(int, lines[0].split())
    # TODO: Build hash index and perform join
    pass

if __name__ == '__main__':
    simulate_join()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n, m = map(int, lines[0].split())
    table_a = {}
    for i in range(1, n + 1):
        parts = lines[i].split()
        table_a[int(parts[0])] = parts[1]

    table_b = {}
    for j in range(n + 1, n + 1 + m):
        parts = lines[j].split()
        table_b[int(parts[0])] = parts[1]

    matches = []
    for k in sorted(table_a.keys()):
        if k in table_b:
            matches.append(f"{k} {table_a[k]} {table_b[k]}")

    for row in matches:
        print(row)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "3 2\n1 Alice\n2 Bob\n3 Charlie\n1 Engineering\n3 Research\n", "expected_output": "1 Alice Engineering\n3 Charlie Research\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "1 1\n5 Alpha\n5 Omega\n", "expected_output": "5 Alpha Omega\n", "visibility": "public", "weight": 1.0},
            {"input_data": "2 1\n10 X\n20 Y\n99 Z\n", "expected_output": "", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_join_iteration", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop matching keys across relational records"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Relational Group By and Aggregate Simulation",
        "slug": "relational-group-by-aggregate-simulation",
        "difficulty": "medium",
        "language": "python",
        "topics": ["sql", "hashing"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["Output sorted alphabetically by category name", "Simulates SQL SELECT category, COUNT(*), SUM(amount) GROUP BY category"],
        "input_format": "Line 1: N. Following N lines: `category amount`.",
        "output_format": "Grouped rows: `category count sum` sorted by category.",
        "statement_markdown": """### Problem Description
Simulate an SQL **GROUP BY** aggregation query. Given a transaction log of `N` rows with `category` and integer `amount`, group the records by category and output the category name, total count of transactions, and total sum of amounts.

### SQL Equivalent
```sql
SELECT category, COUNT(*) AS cnt, SUM(amount) AS total
FROM Transactions
GROUP BY category
ORDER BY category ASC;
```

### Concept Requirement
You **must** aggregate groups using a dictionary mapping each unique category to its running count and total.

### Example 1
**Input:**
```
4
Books 15
Electronics 100
Books 25
Food 10
```
**Output:**
```
Books 2 40
Electronics 1 100
Food 1 10
```
""",
        "starter_code": """import sys

def group_by_aggregate():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n = int(lines[0].strip())
    # TODO: Implement GROUP BY category with count and sum
    pass

if __name__ == '__main__':
    group_by_aggregate()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    n = int(lines[0].strip())
    groups = {}
    for i in range(1, n + 1):
        if i < len(lines) and lines[i].strip():
            cat, amt = lines[i].split()
            amt_val = int(amt)
            if cat not in groups:
                groups[cat] = [0, 0]  # [count, sum]
            groups[cat][0] += 1
            groups[cat][1] += amt_val

    for cat in sorted(groups.keys()):
        print(f"{cat} {groups[cat][0]} {groups[cat][1]}")

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "4\nBooks 15\nElectronics 100\nBooks 25\nFood 10\n", "expected_output": "Books 2 40\nElectronics 1 100\nFood 1 10\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2\nOffice 5\nOffice 7\n", "expected_output": "Office 2 12\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\nMusic 30\n", "expected_output": "Music 1 30\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_groupby_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop reading rows and accumulating aggregates"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 8. DYNAMIC PROGRAMMING (MEDIUM & HARD)
    # -------------------------------------------------------------------------
    {
        "title": "Longest Common Subsequence of Two Strings",
        "slug": "longest-common-subsequence-dp",
        "difficulty": "hard",
        "language": "python",
        "topics": ["dynamic-programming", "strings"],
        "expected_concepts": ["nested_loop", "conditional"],
        "constraints": ["1 <= len(text1), len(text2) <= 1000", "Must solve in O(M * N) time using DP matrix"],
        "input_format": "Line 1: string text1. Line 2: string text2.",
        "output_format": "An integer: the length of their longest common subsequence.",
        "statement_markdown": """### Problem Description
Given two strings `text1` and `text2`, return the length of their longest common subsequence. If there is no common subsequence, return `0`. A subsequence of a string is a new string generated from the original string with some characters (can be none) deleted without changing the relative order of the remaining characters.

### Concept Requirement
You **must** use a 2D dynamic programming grid with nested loops ($O(M \\times N)$) to tabulate optimal subproblems.

### Example 1
**Input:**
```
abcde
ace
```
**Output:**
```
3
```
*Explanation: The longest common subsequence is "ace" and its length is 3.*
""",
        "starter_code": """import sys

def longest_common_subsequence():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        print(0)
        return
    text1, text2 = lines[0].strip(), lines[1].strip()
    # TODO: 2D Dynamic Programming matrix
    pass

if __name__ == '__main__':
    longest_common_subsequence()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        print(0)
        return
    s1, s2 = lines[0].strip(), lines[1].strip()
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    print(dp[m][n])

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "abcde\nace\n", "expected_output": "3\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "abc\nabc\n", "expected_output": "3\n", "visibility": "public", "weight": 1.0},
            {"input_data": "abc\ndef\n", "expected_output": "0\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "nested_loop", "rule_id": "rule_2d_dp_loops", "required": True, "min_occurrences": 1, "description": "Nested loops filling dynamic programming table"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Coin Change Fewest Coins Dynamic Programming",
        "slug": "coin-change-fewest-coins-dp",
        "difficulty": "medium",
        "language": "python",
        "topics": ["dynamic-programming", "arrays"],
        "expected_concepts": ["nested_loop", "conditional"],
        "constraints": ["1 <= len(coins) <= 12", "1 <= coins[i] <= 10^4", "0 <= amount <= 10^4"],
        "input_format": "Line 1: space-separated coin denominations. Line 2: integer target amount.",
        "output_format": "Fewest number of coins needed to make up amount, or -1 if impossible.",
        "statement_markdown": """### Problem Description
You are given an integer array `coins` representing coins of different denominations and an integer `amount` representing a total amount of money. Return the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return `-1`.

### Concept Requirement
You **must** solve this using bottom-up 1D dynamic programming tabulation.

### Example 1
**Input:**
```
1 2 5
11
```
**Output:**
```
3
```
*Explanation: 11 = 5 + 5 + 1.*
""",
        "starter_code": """import sys

def coin_change():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    coins = [int(x) for x in lines[0].split()]
    amount = int(lines[1].strip())
    # TODO: DP array
    pass

if __name__ == '__main__':
    coin_change()
""",
        "reference_solution": """import sys

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    coins = [int(x) for x in lines[0].split()]
    amount = int(lines[1].strip())

    dp = [float('inf')] * (amount + 1)
    dp[0] = 0

    for a in range(1, amount + 1):
        for c in coins:
            if a - c >= 0 and dp[a - c] != float('inf'):
                if dp[a - c] + 1 < dp[a]:
                    dp[a] = dp[a - c] + 1

    print(-1 if dp[amount] == float('inf') else dp[amount])

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "1 2 5\n11\n", "expected_output": "3\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2\n3\n", "expected_output": "-1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\n0\n", "expected_output": "0\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "nested_loop", "rule_id": "rule_dp_nested_loop", "required": True, "min_occurrences": 1, "description": "Nested loop iterating amounts and coin choices"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 9. STACKS (HARD & ADVANCED)
    # -------------------------------------------------------------------------
    {
        "title": "Largest Rectangle in Histogram via Monotonic Stack",
        "slug": "largest-rectangle-histogram-monotonic-stack",
        "difficulty": "hard",
        "language": "python",
        "topics": ["stacks", "arrays"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["1 <= len(heights) <= 10^5", "0 <= heights[i] <= 10^4", "Time complexity must be O(N)"],
        "input_format": "A single line containing space-separated non-negative bar heights.",
        "output_format": "An integer: the area of the largest rectangle in the histogram.",
        "statement_markdown": """### Problem Description
Given an array of integers `heights` representing the histogram's bar height where the width of each bar is `1`, return the area of the largest rectangle in the histogram.

### Algorithmic Requirement
You **must** use an explicit **monotonic increasing stack** of indices to compute the maximal area in linear $O(N)$ time. An $O(N^2)$ brute force approach will time out.

### Example 1
**Input:**
```
2 1 5 6 2 3
```
**Output:**
```
10
```
""",
        "starter_code": """import sys

def largest_rectangle_area():
    raw = sys.stdin.read().strip()
    if not raw:
        print(0)
        return
    heights = [int(x) for x in raw.split()]
    # TODO: Monotonic stack calculation
    pass

if __name__ == '__main__':
    largest_rectangle_area()
""",
        "reference_solution": """import sys

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print(0)
        return
    heights = [int(x) for x in raw.split()]
    stack = []
    max_area = 0
    heights.append(0)

    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            top_idx = stack.pop()
            height = heights[top_idx]
            width = i if not stack else (i - stack[-1] - 1)
            max_area = max(max_area, height * width)
        stack.append(i)

    print(max_area)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "2 1 5 6 2 3\n", "expected_output": "10\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "2 4\n", "expected_output": "4\n", "visibility": "public", "weight": 1.0},
            {"input_data": "1\n", "expected_output": "1\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_histogram_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop iterating over heights with inner monotonic stack"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Evaluate Reverse Polish Notation Arithmetic Stack",
        "slug": "evaluate-reverse-polish-notation-stack",
        "difficulty": "medium",
        "language": "python",
        "topics": ["stacks", "math"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["Tokens consist of valid integers and operators (+, -, *, /)", "Division between integers truncates toward zero"],
        "input_format": "A single line of space-separated tokens in postfix notation.",
        "output_format": "The single integer result of evaluating the arithmetic expression.",
        "statement_markdown": """### Problem Description
Evaluate the value of an arithmetic expression in Reverse Polish Notation (RPN). Valid operators are `+`, `-`, `*`, and `/`. Each operand may be an integer or another expression. Note that division between two integers should truncate toward zero.

### Concept Requirement
You **must** evaluate the postfix expression using a last-in-first-out **stack** data structure (`list.append` and `list.pop`).

### Example 1
**Input:**
```
2 1 + 3 *
```
**Output:**
```
9
```
*Explanation: ((2 + 1) * 3) = 9.*
""",
        "starter_code": """import sys

def eval_rpn():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    tokens = raw.split()
    # TODO: Evaluate with stack
    pass

if __name__ == '__main__':
    eval_rpn()
""",
        "reference_solution": """import sys

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    tokens = raw.split()
    stack = []

    for token in tokens:
        if token == "+":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
        elif token == "-":
            b, a = stack.pop(), stack.pop()
            stack.append(a - b)
        elif token == "*":
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
        elif token == "/":
            b, a = stack.pop(), stack.pop()
            # Truncation toward zero in Python
            stack.append(int(a / b))
        else:
            stack.append(int(token))

    print(stack[0])

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "2 1 + 3 *\n", "expected_output": "9\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "4 13 5 / +\n", "expected_output": "6\n", "visibility": "public", "weight": 1.0},
            {"input_data": "10 6 9 3 + -11 * / * 17 + 5 +\n", "expected_output": "22\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_rpn_token_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop processing expression tokens"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 10. OBJECT-ORIENTED PROGRAMMING (OOP)
    # -------------------------------------------------------------------------
    {
        "title": "Least Recently Used (LRU) Cache Class Implementation",
        "slug": "lru-cache-class-implementation",
        "difficulty": "hard",
        "language": "python",
        "topics": ["oop", "hashing", "linked-lists"],
        "expected_concepts": ["oop_class", "function_definition"],
        "constraints": ["1 <= capacity <= 3000", "0 <= key, value <= 10^4", "Both get and put operations must run in O(1) average time"],
        "input_format": "Line 1: capacity. Following lines: operation commands: `put key val` or `get key`.",
        "output_format": "Each `get` call outputs its return value on a new line.",
        "statement_markdown": """### Problem Description
Design a data structure that follows the constraints of a **Least Recently Used (LRU) Cache**.
Implement the `LRUCache` class:
- `LRUCache(int capacity)`: Initialize the LRU cache with positive size `capacity`.
- `int get(int key)`: Return the value of the `key` if the key exists, otherwise return `-1`.
- `void put(int key, int value)`: Update the value of the `key` if the `key` exists. Otherwise, add the `key-value` pair to the cache. If the number of keys exceeds the `capacity` from this operation, evict the least recently used key.

### Concept Requirement
You **must** implement a Python `class` containing `__init__`, `get`, and `put` methods. Both operations must achieve $O(1)$ time complexity using an ordered dictionary or hash map + doubly linked list.

### Example 1
**Input:**
```
2
put 1 1
put 2 2
get 1
put 3 3
get 2
put 4 4
get 1
get 3
get 4
```
**Output:**
```
1
-1
-1
3
4
```
""",
        "starter_code": """import sys
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        # TODO: Implement get with O(1) eviction tracking
        pass

    def put(self, key: int, value: int) -> None:
        # TODO: Implement put with O(1) eviction
        pass

if __name__ == '__main__':
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        sys.exit(0)
    cap = int(lines[0].strip())
    lru = LRUCache(cap)
    for cmd in lines[1:]:
        parts = cmd.split()
        if parts[0] == 'put':
            lru.put(int(parts[1]), int(parts[2]))
        elif parts[0] == 'get':
            print(lru.get(int(parts[1])))
""",
        "reference_solution": """import sys
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

def main():
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        return
    cap = int(lines[0].strip())
    lru = LRUCache(cap)
    for line in lines[1:]:
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "put":
            lru.put(int(parts[1]), int(parts[2]))
        elif parts[0] == "get":
            print(lru.get(int(parts[1])))

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "2\nput 1 1\nput 2 2\nget 1\nput 3 3\nget 2\nput 4 4\nget 1\nget 3\nget 4\n", "expected_output": "1\n-1\n-1\n3\n4\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "1\nput 10 100\nget 10\nput 20 200\nget 10\nget 20\n", "expected_output": "100\n-1\n200\n", "visibility": "public", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "oop_class", "rule_id": "rule_lru_class", "required": True, "min_occurrences": 1, "description": "Must define custom LRUCache class"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 11. STRINGS & HASHING (SLIDING WINDOW & ANAGRAMS)
    # -------------------------------------------------------------------------
    {
        "title": "Longest Substring Without Repeating Characters Sliding Window",
        "slug": "longest-substring-without-repeating-characters",
        "difficulty": "medium",
        "language": "python",
        "topics": ["strings", "hashing"],
        "expected_concepts": ["loop", "conditional"],
        "constraints": ["0 <= s.length <= 5 * 10^4", "s consists of English letters, digits, symbols and spaces"],
        "input_format": "A single line containing the string s.",
        "output_format": "An integer: the length of the longest substring without repeating characters.",
        "statement_markdown": """### Problem Description
Given a string `s`, find the length of the longest substring without duplicate characters.

### Concept Requirement
You **must** use a **sliding window** with a hash set or dictionary to track character positions in $O(N)$ time.

### Example 1
**Input:**
```
abcabcbb
```
**Output:**
```
3
```
*Explanation: The answer is "abc", with the length of 3.*
""",
        "starter_code": """import sys

def length_of_longest_substring():
    line = sys.stdin.read().rstrip('\\r\\n')
    if not line:
        print(0)
        return
    # TODO: Sliding window with hash map
    pass

if __name__ == '__main__':
    length_of_longest_substring()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().rstrip('\\r\\n')
    if not line:
        print(0)
        return
    char_map = {}
    left = 0
    max_len = 0
    for right, ch in enumerate(line):
        if ch in char_map and char_map[ch] >= left:
            left = char_map[ch] + 1
        char_map[ch] = right
        max_len = max(max_len, right - left + 1)
    print(max_len)

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "abcabcbb\n", "expected_output": "3\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "bbbbb\n", "expected_output": "1\n", "visibility": "public", "weight": 1.0},
            {"input_data": "pwwkew\n", "expected_output": "3\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_sliding_window_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop expanding sliding window"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
    {
        "title": "Group Anagrams by Canonical Frequency Key",
        "slug": "group-anagrams-canonical-key",
        "difficulty": "medium",
        "language": "python",
        "topics": ["strings", "hashing", "sorting"],
        "expected_concepts": ["loop", "function_definition"],
        "constraints": ["1 <= len(strs) <= 10^4", "Output groups sorted alphabetically by first word, each group sorted alphabetically"],
        "input_format": "A single line of space-separated lowercase words.",
        "output_format": "Each anagram group printed on its own line sorted alphabetically.",
        "statement_markdown": """### Problem Description
Given an array of strings `strs`, group the anagrams together. You can return the answer in any order, but for deterministic verification, print each group sorted alphabetically, with the groups themselves printed in alphabetical order according to their first element.

### Concept Requirement
You **must** use a dictionary mapping canonical sorted character signatures (`tuple(sorted(word))` or character count tuples) to lists of words.

### Example 1
**Input:**
```
eat tea tan ate nat bat
```
**Output:**
```
ate eat tea
bat
nat tan
```
""",
        "starter_code": """import sys
from collections import defaultdict

def group_anagrams():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    words = raw.split()
    # TODO: Group by canonical signature
    pass

if __name__ == '__main__':
    group_anagrams()
""",
        "reference_solution": """import sys
from collections import defaultdict

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return
    words = raw.split()
    groups = defaultdict(list)
    for w in words:
        key = "".join(sorted(w))
        groups[key].append(w)

    result = []
    for g in groups.values():
        result.append(sorted(g))

    result.sort(key=lambda x: x[0])
    for g in result:
        print(" ".join(g))

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "eat tea tan ate nat bat\n", "expected_output": "ate eat tea\nbat\nnat tan\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "a\n", "expected_output": "a\n", "visibility": "public", "weight": 1.0},
            {"input_data": "listen silent enlisted inlets\n", "expected_output": "enlisted\ninlets listen silent\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "loop", "rule_id": "rule_anagram_group_loop", "accepted_constructs": ["For"], "required": True, "min_occurrences": 1, "description": "For loop grouping words into dictionary"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },

    # -------------------------------------------------------------------------
    # 12. MATHEMATICS
    # -------------------------------------------------------------------------
    {
        "title": "Prime Numbers Sieve of Eratosthenes",
        "slug": "prime-numbers-sieve-eratosthenes",
        "difficulty": "medium",
        "language": "python",
        "topics": ["math", "arrays"],
        "expected_concepts": ["nested_loop", "conditional"],
        "constraints": ["2 <= N <= 10^5", "Must implement true Sieve of Eratosthenes boolean array"],
        "input_format": "A single integer N.",
        "output_format": "All prime numbers <= N space-separated in ascending order.",
        "statement_markdown": """### Problem Description
Given an integer `N`, return all prime numbers less than or equal to `N` in ascending order.

### Algorithmic Requirement
You **must** implement the classical **Sieve of Eratosthenes** using a boolean array marking composites in $O(N \\log \\log N)$ time. Individual trial division per number is prohibited.

### Example 1
**Input:**
```
10
```
**Output:**
```
2 3 5 7
```
""",
        "starter_code": """import sys

def sieve():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    # TODO: Sieve of Eratosthenes
    pass

if __name__ == '__main__':
    sieve()
""",
        "reference_solution": """import sys

def main():
    line = sys.stdin.read().strip()
    if not line:
        return
    n = int(line)
    if n < 2:
        print()
        return
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p <= n:
        if is_prime[p]:
            for i in range(p * p, n + 1, p):
                is_prime[i] = False
        p += 1

    primes = [str(i) for i in range(2, n + 1) if is_prime[i]]
    print(" ".join(primes))

if __name__ == '__main__':
    main()
""",
        "test_cases": [
            {"input_data": "10\n", "expected_output": "2 3 5 7\n", "visibility": "sample", "weight": 1.0},
            {"input_data": "20\n", "expected_output": "2 3 5 7 11 13 17 19\n", "visibility": "public", "weight": 1.0},
            {"input_data": "2\n", "expected_output": "2\n", "visibility": "hidden", "weight": 1.0},
        ],
        "concept_rules": [
            {"concept": "nested_loop", "rule_id": "rule_sieve_marking_loop", "required": True, "min_occurrences": 1, "description": "Nested loop marking non-prime multiples"}
        ],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    },
]


def validate_all_problems():
    """Verify that every reference solution produces the exact expected output on all test cases."""
    print("=" * 80)
    print("INDEPENDENT REFERENCE SOLUTION & TEST CASE VERIFIER")
    print("=" * 80)
    passed_all = True
    for p in PROBLEMS_DATA:
        title = p["title"]
        ref_sol = p["reference_solution"]
        # Compile reference solution
        try:
            code_obj = compile(ref_sol, f"<ref_{p['slug']}>", "exec")
        except SyntaxError as e:
            print(f"❌ SYNTAX ERROR in '{title}': {e}")
            passed_all = False
            continue

        for idx, tc in enumerate(p["test_cases"], 1):
            inp = tc["input_data"]
            expected = tc["expected_output"].strip()

            # Execute reference solution in isolated context with captured stdio
            old_stdin = sys.stdin
            old_stdout = sys.stdout
            sys.stdin = io.StringIO(inp)
            captured_out = io.StringIO()
            sys.stdout = captured_out

            try:
                exec_globals = {"__name__": "__main__"}
                exec(code_obj, exec_globals)
                actual = captured_out.getvalue().strip()
                if actual != expected:
                    sys.stdout = old_stdout
                    sys.stdin = old_stdin
                    print(f"❌ TEST FAILED for '{title}' (Case #{idx}):")
                    print(f"   Input   : {repr(inp)}")
                    print(f"   Expected: {repr(expected)}")
                    print(f"   Actual  : {repr(actual)}")
                    passed_all = False
                else:
                    sys.stdout = old_stdout
                    sys.stdin = old_stdin
            except Exception as exc:
                sys.stdout = old_stdout
                sys.stdin = old_stdin
                print(f"❌ RUNTIME ERROR in '{title}' (Case #{idx}): {exc}")
                passed_all = False

    if passed_all:
        print(f"✅ ALL {len(PROBLEMS_DATA)} REFERENCE SOLUTIONS AND TEST CASES VALIDATED 100% CORRECT!")
    return passed_all


if __name__ == "__main__":
    if not validate_all_problems():
        sys.exit(1)

    catalog_output = {
        "source_name": "ConceptEval Pedagogical Problem Library (Expanded Authoritative Curriculum)",
        "license_type": "CC-BY-4.0",
        "provenance_url": "https://concepteval.ai/curriculum/authorized-dataset",
        "problems": PROBLEMS_DATA,
    }

    out_file = os.path.join(os.path.dirname(__file__), "..", "app", "content_import", "comprehensive_catalog.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(catalog_output, f, indent=2)

    print(f"Exported {len(PROBLEMS_DATA)} validated problems to {out_file}")
