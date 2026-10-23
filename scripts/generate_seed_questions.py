import json
import uuid
from pathlib import Path

questions = [
    # --- DSA (difficulty 1) ---
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 1,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the time complexity of accessing an element in an array by its numerical index?",
        "options": [
            {"id": "opt_a", "text": "O(1) constant time"},
            {"id": "opt_b", "text": "O(N) linear time"},
            {"id": "opt_c", "text": "O(log N) logarithmic time"},
            {"id": "opt_d", "text": "O(N^2) quadratic time"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Arrays occupy contiguous memory, allowing direct index calculation via base_address + (index * element_size) in O(1) time.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 1,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "Which linear data structure enforces a First-In, First-Out (FIFO) access order?",
        "options": [
            {"id": "opt_a", "text": "Queue"},
            {"id": "opt_b", "text": "Stack"},
            {"id": "opt_c", "text": "Binary Search Tree"},
            {"id": "opt_d", "text": "Max Heap"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "A Queue processes elements in the exact order they arrive (FIFO), whereas a Stack is LIFO.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 1,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "In a standard singly linked list with only a head pointer, what is the time complexity to insert a new node at the very beginning?",
        "options": [
            {"id": "opt_a", "text": "O(1)"},
            {"id": "opt_b", "text": "O(N)"},
            {"id": "opt_c", "text": "O(log N)"},
            {"id": "opt_d", "text": "O(N log N)"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Inserting at the head requires pointing the new node to current head and updating the head pointer, taking constant O(1) time.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 1,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "Which searching algorithm requires the input array to be sorted beforehand?",
        "options": [
            {"id": "opt_a", "text": "Binary Search"},
            {"id": "opt_b", "text": "Linear Search"},
            {"id": "opt_c", "text": "Breadth-First Search"},
            {"id": "opt_d", "text": "Depth-First Search"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Binary search divides the search space in half at each step based on order comparison, requiring a sorted sequence.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- DSA (difficulty 2) ---
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 2,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the worst-case time complexity of QuickSort when a naive pivot (e.g. always first element) is chosen on an already sorted array?",
        "options": [
            {"id": "opt_a", "text": "O(N^2)"},
            {"id": "opt_b", "text": "O(N log N)"},
            {"id": "opt_c", "text": "O(N)"},
            {"id": "opt_d", "text": "O(log N)"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "If the pivot divides the problem into sizes 0 and N-1 on every partition, recursion depth becomes N, resulting in O(N^2) comparisons.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 2,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "Which algorithm effectively detects a cycle in a singly linked list in O(1) auxiliary space?",
        "options": [
            {"id": "opt_a", "text": "Floyd's Tortoise and Hare two-pointer algorithm"},
            {"id": "opt_b", "text": "Dijkstra's shortest path algorithm"},
            {"id": "opt_c", "text": "Kruskal's minimum spanning tree algorithm"},
            {"id": "opt_d", "text": "Tarjan's strongly connected components algorithm"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Floyd's algorithm advances a slow pointer by 1 and a fast pointer by 2. If a cycle exists, they must collide in O(N) time with O(1) auxiliary space.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 2,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "When implementing a Hash Map with separate chaining, what is the average lookup time assuming uniform hash distribution?",
        "options": [
            {"id": "opt_a", "text": "O(1)"},
            {"id": "opt_b", "text": "O(log N)"},
            {"id": "opt_c", "text": "O(N)"},
            {"id": "opt_d", "text": "O(sqrt(N))"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "With a bounded load factor and uniform hash distribution, bucket chain lengths are bounded by a small constant on average, yielding O(1) lookup.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 2,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "Which data structure is most suitable for finding the Kth largest element in a continuous stream of numbers with O(log K) insertion?",
        "options": [
            {"id": "opt_a", "text": "Min-Heap of size K"},
            {"id": "opt_b", "text": "Max-Heap of size K"},
            {"id": "opt_c", "text": "Doubly Linked List"},
            {"id": "opt_d", "text": "Circular Queue of size K"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Maintaining a Min-Heap of size K keeps the K largest elements seen so far; the root is always the Kth largest element.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- DSA (difficulty 3) ---
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 3,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "In Tarjan's algorithm for finding Strongly Connected Components (SCCs), what does the low-link value low[u] represent?",
        "options": [
            {"id": "opt_a", "text": "Smallest discovery time reachable from u via DFS tree and back edges in the active recursion stack"},
            {"id": "opt_b", "text": "The minimum indegree of any vertex in the component containing u"},
            {"id": "opt_c", "text": "The total number of cycle edges passing through vertex u"},
            {"id": "opt_d", "text": "The shortest geodesic distance from source vertex to u"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "low[u] tracks the lowest discovery timestamp reachable from the subtree rooted at u using back-edges to vertices currently on the recursion stack.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 3,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the amortized cost per operation in a Disjoint Set Union (DSU) data structure utilizing both Path Compression and Union by Rank?",
        "options": [
            {"id": "opt_a", "text": "O(alpha(N)) where alpha is the inverse Ackermann function"},
            {"id": "opt_b", "text": "O(log N)"},
            {"id": "opt_c", "text": "O(1) strict worst-case"},
            {"id": "opt_d", "text": "O(log(log N))"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Combining union by rank and path compression achieves O(alpha(N)) amortized time, which is practically <= 4 for all conceivable values of N.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 3,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "When answering dynamic range minimum queries with point updates on an array of length N, what are the query and update time complexities using a Segment Tree?",
        "options": [
            {"id": "opt_a", "text": "Query O(log N), Update O(log N)"},
            {"id": "opt_b", "text": "Query O(1), Update O(N)"},
            {"id": "opt_c", "text": "Query O(log N), Update O(1)"},
            {"id": "opt_d", "text": "Query O(sqrt(N)), Update O(1)"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "A Segment Tree allows tree traversal of depth log N for both range queries and leaf point updates.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "dsa",
        "type": "skill",
        "difficulty": 3,
        "language": None,
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the space complexity of an Aho-Corasick automaton built over a set of patterns of total length L with an alphabet size Sigma?",
        "options": [
            {"id": "opt_a", "text": "O(L * Sigma)"},
            {"id": "opt_b", "text": "O(L^2)"},
            {"id": "opt_c", "text": "O(2^L)"},
            {"id": "opt_d", "text": "O(L * log Sigma)"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The trie structure has at most L states, with transitions for each alphabet character, resulting in O(L * Sigma) memory.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- PYTHON (difficulty 1) ---
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 1,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "Which of the following built-in data types in Python is immutable?",
        "options": [
            {"id": "opt_a", "text": "tuple"},
            {"id": "opt_b", "text": "list"},
            {"id": "opt_c", "text": "dict"},
            {"id": "opt_d", "text": "set"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Tuples are immutable sequences; once instantiated, their elements cannot be appended, removed, or reassigned.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 1,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the output of the expression `bool([])` in standard Python?",
        "options": [
            {"id": "opt_a", "text": "False"},
            {"id": "opt_b", "text": "True"},
            {"id": "opt_c", "text": "None"},
            {"id": "opt_d", "text": "TypeError"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "In Python truth-value testing, empty collections such as [], {}, (), and '' evaluate to False.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 1,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "Which keyword is used in Python to define a generator function that yields values lazily?",
        "options": [
            {"id": "opt_a", "text": "yield"},
            {"id": "opt_b", "text": "return"},
            {"id": "opt_c", "text": "produce"},
            {"id": "opt_d", "text": "emit"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The yield keyword transforms a function into a generator, yielding control and states lazily one element at a time.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 1,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "What does `list.pop()` do when called with no arguments in Python?",
        "options": [
            {"id": "opt_a", "text": "Removes and returns the last element in the list"},
            {"id": "opt_b", "text": "Removes and returns the first element in the list"},
            {"id": "opt_c", "text": "Clears all elements in the list"},
            {"id": "opt_d", "text": "Raises a TypeError"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "By default, list.pop() takes index=-1 and removes and returns the rightmost element in O(1) time.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- PYTHON (difficulty 2) ---
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 2,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "What happens when a default parameter value in a Python function definition is a mutable object like `def append_to(item, target=[]):`?",
        "options": [
            {"id": "opt_a", "text": "The list is evaluated once at function definition time, persisting state across multiple calls"},
            {"id": "opt_b", "text": "A fresh list is allocated dynamically on every invocation"},
            {"id": "opt_c", "text": "Python raises a SyntaxError at compile time"},
            {"id": "opt_d", "text": "The list becomes immutable within the function scope"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Default arguments in Python are bound when the function definition is executed, leading to shared state bugs if mutated.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 2,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "Which dunder methods must an object implement to participate in the Context Manager protocol (`with` statement)?",
        "options": [
            {"id": "opt_a", "text": "__enter__ and __exit__"},
            {"id": "opt_b", "text": "__start__ and __finish__"},
            {"id": "opt_c", "text": "__open__ and __close__"},
            {"id": "opt_d", "text": "__iter__ and __next__"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The context management protocol requires __enter__ (called on entry) and __exit__ (called on exit, handling exceptions).",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 2,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "How does the Python Global Interpreter Lock (GIL) impact CPython multithreading for pure CPU-bound tasks?",
        "options": [
            {"id": "opt_a", "text": "Prevents multiple native threads from executing Python bytecodes concurrently on multiple cores"},
            {"id": "opt_b", "text": "Automatically parallelizes loop iterations across physical CPU cores"},
            {"id": "opt_c", "text": "Blocks asynchronous I/O syscalls until thread completion"},
            {"id": "opt_d", "text": "Ensures automatic lock-free synchronization for shared global state"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The GIL ensures memory safety in CPython by permitting only one native thread to hold the Python interpreter lock at a time.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 2,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the primary role of `functools.wraps` when authoring custom Python decorators?",
        "options": [
            {"id": "opt_a", "text": "Copies docstring, function name, and signature metadata from the original function to the wrapper"},
            {"id": "opt_b", "text": "Caches function return values based on positional arguments"},
            {"id": "opt_c", "text": "Converts synchronous functions into asyncio coroutines"},
            {"id": "opt_d", "text": "Enforces runtime type validation on parameters"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "functools.wraps updates the wrapper function to mirror the original __name__, __doc__, and __annotations__ attributes.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- PYTHON (difficulty 3) ---
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 3,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "In the Python descriptor protocol, what distinguishes a data descriptor from a non-data descriptor?",
        "options": [
            {"id": "opt_a", "text": "A data descriptor defines __set__ or __delete__, overriding instance dictionary lookup in attribute resolution"},
            {"id": "opt_b", "text": "A data descriptor cannot hold primitive numeric values"},
            {"id": "opt_c", "text": "A non-data descriptor requires explicit inheritance from type"},
            {"id": "opt_d", "text": "A data descriptor cannot implement __get__"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "If an object defines __set__ or __delete__, it is a data descriptor. CPython checks data descriptors before looking in an instance __dict__.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 3,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "What does `__slots__` achieve when declared on a Python class definition?",
        "options": [
            {"id": "opt_a", "text": "Suppresses default __dict__ creation per instance, minimizing memory footprint and accelerating attribute access"},
            {"id": "opt_b", "text": "Locks all attributes against mutation, enforcing immutability"},
            {"id": "opt_c", "text": "Registers the class as an abstract base class"},
            {"id": "opt_d", "text": "Configures multiprocessing pickling protocols"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "__slots__ reserves space for declared attributes directly in a fixed C array, eliminating the dynamic dictionary memory overhead.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 3,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "How does the Python asyncio event loop manage context variables (`contextvars.ContextVar`) across concurrent tasks?",
        "options": [
            {"id": "opt_a", "text": "Each Task gets a shallow copy of active Context on creation, isolating modifications within that Task hierarchy"},
            {"id": "opt_b", "text": "Context variables are stored in thread-local storage, leaking between tasks running on the same thread"},
            {"id": "opt_c", "text": "Context variables require global mutex locks on every read and write"},
            {"id": "opt_d", "text": "ContextVar cannot be used in asynchronous functions"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "asyncio.create_task copies current Context, ensuring context state propagates to children while protecting peer tasks from mutations.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "python",
        "type": "skill",
        "difficulty": 3,
        "language": "python",
        "career_cluster": "Technology & Engineering",
        "question_text": "When implementing a custom metaclass in Python, what parameters does `__new__(cls, name, bases, dct)` receive?",
        "options": [
            {"id": "opt_a", "text": "The metaclass itself, class name string, tuple of base classes, and class namespace dictionary"},
            {"id": "opt_b", "text": "An instantiated object and constructor kwargs"},
            {"id": "opt_c", "text": "AST node representations of class methods"},
            {"id": "opt_d", "text": "Module scope and bytecode offsets"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "In metaclasses, __new__ is invoked to allocate the class object itself, taking metaclass cls, class name, base class tuple, and class namespace dict.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- CPP (difficulty 1, 2, 3) ---
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 1,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "Which access specifier in C++ makes class members accessible only within the defining class and its derived classes?",
        "options": [
            {"id": "opt_a", "text": "protected"},
            {"id": "opt_b", "text": "private"},
            {"id": "opt_c", "text": "public"},
            {"id": "opt_d", "text": "internal"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "protected members are inaccessible to outside callers, but inherit cleanly into derived classes.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 1,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What operator in C++ is used to access the value stored at a pointer memory address (dereferencing)?",
        "options": [
            {"id": "opt_a", "text": "*"},
            {"id": "opt_b", "text": "&"},
            {"id": "opt_c", "text": "->"},
            {"id": "opt_d", "text": "::"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The asterisk (*) operator dereferences a pointer to read or write the value at the address.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 1,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What header must be included to use `std::vector` in C++?",
        "options": [
            {"id": "opt_a", "text": "<vector>"},
            {"id": "opt_b", "text": "<array>"},
            {"id": "opt_c", "text": "<list>"},
            {"id": "opt_d", "text": "<algorithm>"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "std::vector is defined in the standard <vector> header.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 2,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the primary difference between `std::unique_ptr` and `std::shared_ptr` in modern C++?",
        "options": [
            {"id": "opt_a", "text": "std::unique_ptr enforces exclusive single ownership (non-copyable), while std::shared_ptr manages shared ownership via reference counting"},
            {"id": "opt_b", "text": "std::shared_ptr is allocated on the stack whereas std::unique_ptr is always on heap"},
            {"id": "opt_c", "text": "std::unique_ptr cannot be used with polymorphic classes"},
            {"id": "opt_d", "text": "std::shared_ptr automatically prevents circular reference leaks"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "unique_ptr models exclusive resource ownership with zero runtime overhead; shared_ptr uses atomic reference counting for shared lifetimes.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 2,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "Why should a base class with virtual functions declare a virtual destructor in C++?",
        "options": [
            {"id": "opt_a", "text": "To ensure derived class destructors are properly invoked when deleting derived objects via base pointers"},
            {"id": "opt_b", "text": "To enable pure virtual function overriding"},
            {"id": "opt_c", "text": "To prevent heap allocation of the base class"},
            {"id": "opt_d", "text": "To eliminate the vtable pointer overhead"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Deleting a derived instance through a base pointer with a non-virtual destructor results in undefined behavior and resource leaks.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 2,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What does `std::move` do in C++11 and beyond?",
        "options": [
            {"id": "opt_a", "text": "Unconditionally casts its argument to an rvalue reference, enabling move semantics"},
            {"id": "opt_b", "text": "Copies heap memory asynchronously to another thread"},
            {"id": "opt_c", "text": "Deallocates the source object immediately"},
            {"id": "opt_d", "text": "Converts stack variables into heap pointers"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "std::move performs a static_cast to rvalue reference (T&&), signaling to constructors or assignment operators that resources can be transferred.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 3,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "In C++ template metaprogramming, what does SFINAE describe?",
        "options": [
            {"id": "opt_a", "text": "Substitution Failure Is Not An Error: substitution errors in template overloads discard candidates rather than halting compilation"},
            {"id": "opt_b", "text": "Static Function Inlining And Namespace Allocation Enhancement"},
            {"id": "opt_c", "text": "Single File Inclusion And Native Assembly Execution"},
            {"id": "opt_d", "text": "Synchronized Fast I/O Network Allocation Engine"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "SFINAE allows compile-time overload introspection: if substituting deduced types into a template signature fails, the compiler cleanly drops the overload.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 3,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What guarantees are provided by `std::memory_order_acquire` and `std::memory_order_release` in C++ memory models?",
        "options": [
            {"id": "opt_a", "text": "Synchronizes memory: writes before release in one thread become visible to another thread following acquire on the same atomic variable"},
            {"id": "opt_b", "text": "Total global sequential ordering across all CPU cores on all instructions"},
            {"id": "opt_c", "text": "Eliminates hardware cache coherence invalidations entirely"},
            {"id": "opt_d", "text": "Guarantees execution without CPU branch prediction"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Acquire-release semantics enforce a happens-before relationship between the store-release and load-acquire on the synchronized atomic flag.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "cpp",
        "type": "skill",
        "difficulty": 3,
        "language": "cpp",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the purpose of `std::launder` in C++17?",
        "options": [
            {"id": "opt_a", "text": "Informs the optimizer that a new object was created in storage previously occupied by another object, preventing invalid devirtualization"},
            {"id": "opt_b", "text": "Clears sensitive cryptographic secrets from RAM with zeroes"},
            {"id": "opt_c", "text": "Safely casts pointers between unrelated non-standard layout structs"},
            {"id": "opt_d", "text": "Compresses polymorphic vtable pointer indices"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "std::launder is required when an object with const or reference members or virtual methods is recreated in placement new, preventing UB.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- JAVA (difficulty 1, 2, 3) ---
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 1,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "In Java, which keyword prevents a class from being subclassed (inherited)?",
        "options": [
            {"id": "opt_a", "text": "final"},
            {"id": "opt_b", "text": "static"},
            {"id": "opt_c", "text": "sealed"},
            {"id": "opt_d", "text": "const"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Declaring a Java class final makes it impossible for other classes to extend it (e.g. java.lang.String).",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 1,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the default initial capacity of an `ArrayList` in Java when not specified?",
        "options": [
            {"id": "opt_a", "text": "10"},
            {"id": "opt_b", "text": "16"},
            {"id": "opt_c", "text": "0"},
            {"id": "opt_d", "text": "32"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "In standard OpenJDK / Oracle JDK, an empty ArrayList allocates an underlying array with DEFAULT_CAPACITY = 10 on the first add() operation.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 1,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "Which interface in the Java Collections Framework provides key-value pair mapping without duplicate keys?",
        "options": [
            {"id": "opt_a", "text": "java.util.Map"},
            {"id": "opt_b", "text": "java.util.List"},
            {"id": "opt_c", "text": "java.util.Set"},
            {"id": "opt_d", "text": "java.util.Queue"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "java.util.Map models key-to-value associations where each key maps to at most one value.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 2,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "What is the contract between `equals()` and `hashCode()` in Java?",
        "options": [
            {"id": "opt_a", "text": "If two objects are equal according to equals(), they must produce the identical integer hashCode()"},
            {"id": "opt_b", "text": "If two objects produce the same hashCode(), they must be equal according to equals()"},
            {"id": "opt_c", "text": "hashCode() must return distinct integers for all unequal objects"},
            {"id": "opt_d", "text": "equals() is only evaluated if hashCode() returns a negative number"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The Java contract strictly requires: a.equals(b) == true => a.hashCode() == b.hashCode(), essential for hash-based collections.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 2,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "What internal optimization does Java `HashMap` employ when bucket collision chain length exceeds TREEIFY_THRESHOLD (8)?",
        "options": [
            {"id": "opt_a", "text": "Converts linked list bucket nodes into a balanced Red-Black Tree (TreeNode)"},
            {"id": "opt_b", "text": "Rehashes all keys into a secondary linear probing buffer"},
            {"id": "opt_c", "text": "Evicts the oldest bucket entries via LRU policy"},
            {"id": "opt_d", "text": "Throws a ConcurrentModificationException"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Since Java 8, when a bucket exceeds 8 nodes and table capacity >= 64, it transforms into a Red-Black Tree, improving worst-case search from O(N) to O(log N).",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 2,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "What happens when a thread calls `Thread.join()` on another thread instance in Java?",
        "options": [
            {"id": "opt_a", "text": "The calling thread transitions to WAITING until the target thread terminates"},
            {"id": "opt_b", "text": "The calling thread preempts and interrupts the target thread"},
            {"id": "opt_c", "text": "Both threads merge into a single OS lightweight process"},
            {"id": "opt_d", "text": "The target thread yields its current CPU quantum"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Thread.join() blocks the executing caller until target thread terminates, enabling sequential synchronization.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 3,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "In the Java Virtual Machine, what is Compressed OOPs (Ordinary Object Pointers)?",
        "options": [
            {"id": "opt_a", "text": "Encodes 64-bit object references in 32 bits using 8-byte object alignment on heaps up to 32GB"},
            {"id": "opt_b", "text": "Applies gzip compression to serialized Java bytecode chunks"},
            {"id": "opt_c", "text": "Packs string char arrays into UTF-8 byte buffers"},
            {"id": "opt_d", "text": "Disables escape analysis on short-lived thread-local objects"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Compressed OOPs shifts pointers right by 3 bits (taking advantage of 8-byte alignment), allowing 32-bit pointers to address up to 32GB of heap.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 3,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "What memory visibility guarantee does the `volatile` modifier provide according to the Java Memory Model (JMM)?",
        "options": [
            {"id": "opt_a", "text": "Establishes a happens-before order: writes to a volatile variable are immediately flushed to main memory and visible to subsequent reads"},
            {"id": "opt_b", "text": "Ensures compound check-then-act operations (like count++) are atomic"},
            {"id": "opt_c", "text": "Prevents garbage collection of referenced objects"},
            {"id": "opt_d", "text": "Serializes object states across JVM network sockets"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "volatile guarantees read/write visibility and prevents instruction reordering around the variable, though compound operations still require atomic primitives.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "java",
        "type": "skill",
        "difficulty": 3,
        "language": "java",
        "career_cluster": "Technology & Engineering",
        "question_text": "How do Virtual Threads (Project Loom / Java 21) achieve massive concurrency compared to platform threads?",
        "options": [
            {"id": "opt_a", "text": "User-mode lightweight threads managed by the JVM runtime mounted onto a small carrier pool of OS threads, unmounting on blocking I/O"},
            {"id": "opt_b", "text": "Directly multiplexing kernel interrupts onto GPU shader units"},
            {"id": "opt_c", "text": "Removing runtime stack frames entirely using CPS transformation"},
            {"id": "opt_d", "text": "Forcing all network sockets into epoll reactor loops without thread contexts"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Virtual threads are lightweight JVM-managed tasks that yield their carrier OS thread when encountering blocking operations, permitting millions of concurrent tasks.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- QUANTITATIVE APTITUDE (difficulty 1, 2, 3) ---
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "If an item marked at Rs 800 is sold with a 20% discount, what is its selling price?",
        "options": [
            {"id": "opt_a", "text": "Rs 640"},
            {"id": "opt_b", "text": "Rs 600"},
            {"id": "opt_c", "text": "Rs 680"},
            {"id": "opt_d", "text": "Rs 720"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Discount = 20% of 800 = 160. Selling price = 800 - 160 = Rs 640.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "The ratio of two numbers is 3:5 and their sum is 160. What is the value of the smaller number?",
        "options": [
            {"id": "opt_a", "text": "60"},
            {"id": "opt_b", "text": "40"},
            {"id": "opt_c", "text": "50"},
            {"id": "opt_d", "text": "70"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Total parts = 3 + 5 = 8 parts. 1 part = 160 / 8 = 20. Smaller number = 3 * 20 = 60.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "A train traveling at 72 km/h crosses a pole in 10 seconds. What is the length of the train in meters?",
        "options": [
            {"id": "opt_a", "text": "200 meters"},
            {"id": "opt_b", "text": "180 meters"},
            {"id": "opt_c", "text": "250 meters"},
            {"id": "opt_d", "text": "150 meters"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Speed in m/s = 72 * (5/18) = 20 m/s. Length = Speed * Time = 20 m/s * 10 s = 200 meters.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "Pipe A fills a tank in 6 hours, while Pipe B empties it in 9 hours. If both pipes are opened simultaneously when the tank is empty, in how many hours will the tank become full?",
        "options": [
            {"id": "opt_a", "text": "18 hours"},
            {"id": "opt_b", "text": "15 hours"},
            {"id": "opt_c", "text": "12 hours"},
            {"id": "opt_d", "text": "24 hours"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Net rate per hour = (1/6) - (1/9) = (3 - 2)/18 = 1/18. Hence the tank fills in 18 hours.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "A sum of Rs 10,000 invested at compound interest compounded annually grows to Rs 12,100 in 2 years. What is the annual interest rate?",
        "options": [
            {"id": "opt_a", "text": "10%"},
            {"id": "opt_b", "text": "11%"},
            {"id": "opt_c", "text": "12%"},
            {"id": "opt_d", "text": "9.5%"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "A/P = (1 + r/100)^2 => 12100/10000 = 1.21 => 1 + r/100 = sqrt(1.21) = 1.10 => r = 10%.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "In how many different ways can the letters of the word LEADER be arranged?",
        "options": [
            {"id": "opt_a", "text": "360"},
            {"id": "opt_b", "text": "720"},
            {"id": "opt_c", "text": "180"},
            {"id": "opt_d", "text": "120"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "LEADER has 6 letters with E repeating twice. Total permutations = 6! / 2! = 720 / 2 = 360.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "A bag contains 5 red balls and 4 blue balls. If 3 balls are drawn at random without replacement, what is the probability that exactly 2 are red and 1 is blue?",
        "options": [
            {"id": "opt_a", "text": "10/21"},
            {"id": "opt_b", "text": "5/14"},
            {"id": "opt_c", "text": "20/63"},
            {"id": "opt_d", "text": "15/28"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Favorable outcomes = C(5, 2) * C(4, 1) = 10 * 4 = 40. Total outcomes = C(9, 3) = (9*8*7)/(3*2*1) = 84. Probability = 40 / 84 = 10 / 21.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "Find the remainder when 7^101 is divided by 25.",
        "options": [
            {"id": "opt_a", "text": "7"},
            {"id": "opt_b", "text": "14"},
            {"id": "opt_c", "text": "1"},
            {"id": "opt_d", "text": "18"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "7^1 = 7, 7^2 = 49 = -1 mod 25. Thus 7^4 = 1 mod 25. 101 = 4*25 + 1. So 7^101 = (7^4)^25 * 7 = 1^25 * 7 = 7 mod 25.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "quantitative_aptitude",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "Two runners start simultaneously from the same point on a 400m circular track in opposite directions with speeds of 6 m/s and 4 m/s. After how many seconds will they meet for the second time?",
        "options": [
            {"id": "opt_a", "text": "80 seconds"},
            {"id": "opt_b", "text": "40 seconds"},
            {"id": "opt_c", "text": "100 seconds"},
            {"id": "opt_d", "text": "60 seconds"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Relative speed = 6 + 4 = 10 m/s. Time for 1st meeting = 400 / 10 = 40 seconds. Time for 2nd meeting = 40 * 2 = 80 seconds.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },

    # --- LOGICAL REASONING (difficulty 1, 2, 3) ---
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "Identify the next number in the following sequence: 3, 7, 15, 31, 63, ?",
        "options": [
            {"id": "opt_a", "text": "127"},
            {"id": "opt_b", "text": "125"},
            {"id": "opt_c", "text": "129"},
            {"id": "opt_d", "text": "115"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Each term follows 2*x + 1: 3*2+1=7, 7*2+1=15, 15*2+1=31, 31*2+1=63, 63*2+1=127.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "Pointing to a photograph, a woman says: 'He is the only son of my father-in-law.' How is the man related to the woman?",
        "options": [
            {"id": "opt_a", "text": "Husband"},
            {"id": "opt_b", "text": "Brother-in-law"},
            {"id": "opt_c", "text": "Son"},
            {"id": "opt_d", "text": "Father"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The father-in-law of the woman has only one son. That only son must be the woman's husband.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 1,
        "language": None,
        "career_cluster": "General",
        "question_text": "If in a code language SYSTEM is written as SYSMET, how is FRACTION written?",
        "options": [
            {"id": "opt_a", "text": "CARFNOIT"},
            {"id": "opt_b", "text": "ARFCNOIT"},
            {"id": "opt_c", "text": "CARFTION"},
            {"id": "opt_d", "text": "FRACOITN"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "The word is divided into two equal halves (SYS-TEM) and each half is reversed (SYS-MET). For FRAC-TION, FRAC reversed is CARF, and TION reversed is NOIT, giving CARFNOIT.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "Statements: All engineers are innovators. Some innovators are designers. Conclusions: I. Some engineers are designers. II. All designers are innovators.",
        "options": [
            {"id": "opt_a", "text": "Neither conclusion I nor II logically follows"},
            {"id": "opt_b", "text": "Only conclusion I follows"},
            {"id": "opt_c", "text": "Only conclusion II follows"},
            {"id": "opt_d", "text": "Both conclusions I and II follow"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Engineers and designers are subsets of innovators that do not necessarily intersect. Neither conclusion is guaranteed.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "Five persons (P, Q, R, S, T) sit in a straight line facing North. S is between T and Q. Q is immediately to the left of R. P is to the immediate left of T. Who sits in the exact middle?",
        "options": [
            {"id": "opt_a", "text": "S"},
            {"id": "opt_b", "text": "T"},
            {"id": "opt_c", "text": "Q"},
            {"id": "opt_d", "text": "P"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "From left to right: P, T, S, Q, R. S is at position 3, which is the exact middle.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 2,
        "language": None,
        "career_cluster": "General",
        "question_text": "At what angle do the hour and minute hands of an analog clock meet at 3:30?",
        "options": [
            {"id": "opt_a", "text": "75 degrees"},
            {"id": "opt_b", "text": "80 degrees"},
            {"id": "opt_c", "text": "70 degrees"},
            {"id": "opt_d", "text": "90 degrees"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Angle = |30*H - 5.5*M| = |30*3 - 5.5*30| = |90 - 165| = 75 degrees.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "In an island where Truth-tellers always speak truth and Liars always lie: Person A says 'At least one of us is a Liar' and Person B says nothing. What can be deduced?",
        "options": [
            {"id": "opt_a", "text": "A is a Truth-teller and B is a Liar"},
            {"id": "opt_b", "text": "Both A and B are Liars"},
            {"id": "opt_c", "text": "Both A and B are Truth-tellers"},
            {"id": "opt_d", "text": "A is a Liar and B is a Truth-teller"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "If A were a liar, the statement 'at least one is a liar' would be true, leading to a contradiction. Hence A is a truth-teller, which makes B the liar.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "In a tournament of 8 players with distinct skill ratings where the better player always wins, what is the minimum number of matches required to identify the second best player?",
        "options": [
            {"id": "opt_a", "text": "9 matches"},
            {"id": "opt_b", "text": "7 matches"},
            {"id": "opt_c", "text": "10 matches"},
            {"id": "opt_d", "text": "14 matches"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Using a tournament bracket takes N-1 = 7 matches to find the winner. The second best player must have lost to the winner (log2(8) = 3 candidates). Finding the max among 3 candidates takes 2 more matches: 7 + 2 = 9 matches.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    },
    {
        "topic": "logical_reasoning",
        "type": "aptitude",
        "difficulty": 3,
        "language": None,
        "career_cluster": "General",
        "question_text": "Six boxes A, B, C, D, E, F are stacked vertically. Exactly two boxes are between A and B. C is immediately below B. E is at the top. D is above F. If A is below B, where is D located from top?",
        "options": [
            {"id": "opt_a", "text": "Second from the top"},
            {"id": "opt_b", "text": "Third from the top"},
            {"id": "opt_c", "text": "Bottom box"},
            {"id": "opt_d", "text": "Fourth from the top"}
        ],
        "correct_option_id": "opt_a",
        "explanation": "Arrangement top-to-bottom: E(1), D(2), B(3), C(4), F(5), A(6). Exactly two boxes (C, F) are between B and A. D is above F. Thus D is second from the top.",
        "source_note": "Original vocational diagnostic question authored for AI Career Navigator",
        "status": "draft"
    }
]

# Ensure stable UUIDs based on topic, difficulty and question_text
for q in questions:
    ns = uuid.NAMESPACE_DNS
    q["id"] = str(uuid.uuid5(ns, f"{q['topic']}:{q['difficulty']}:{q['question_text']}"))

out_path = Path("app/data/seed/test_questions.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"questions": questions}, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Generated {len(questions)} original diagnostic test questions in {out_path}.")
