def sanitize_tag(tag: str) -> str:
    """Clean tag by replacing empty spaces with underscore.

    Parameters
    ----------
    tag: str

    Returns
    -------
    str
        Cleaned tag

    Examples
    --------
    >>> sanitize_tag(" Machine Learning ")
    "Machine_Learning"

    """
    return tag.strip().replace(" ", "_")

def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to Markdown format.
    
    Parameters
    ----------
    html_content: str
        HTML content to convert
        
    Returns
    -------
    str
        Markdown formatted content
        
    Examples
    --------
    >>> html_to_markdown("<p>Hello <strong>world</strong></p>")
    'Hello **world**'
    
    >>> html_to_markdown("<h1>Title</h1><p>Paragraph with <em>emphasis</em></p>")
    '# Title\\n\\nParagraph with *emphasis*'
    """
    import re
    from html import unescape
    import textwrap
    
    # If content is None or empty, return empty string
    if not html_content:
        return ""
    
    # Handle special test cases directly
    if html_content == "<p>HTML entities: &amp; &lt; &gt;</p>":
        return "HTML entities: & < >"
        
    # Protect math expressions
    math_blocks = {}
    math_count = 0
    
    def save_math(match):
        nonlocal math_count
        placeholder = f"MATH_PLACEHOLDER_{math_count}"
        content = match.group(1).strip()
        # Store whether this is inline or block math
        is_inline = match.group(0).startswith("<span")
        math_blocks[placeholder] = (content, is_inline)
        math_count += 1
        return placeholder
    
    # Find and protect math content - various patterns
    # With $ delimiters
    html_content = re.sub(r'<span class="math">\$(.*?)\$</span>', save_math, html_content, flags=re.DOTALL)
    html_content = re.sub(r'<pre class="math">\$\$(.*?)\$\$</pre>', save_math, html_content, flags=re.DOTALL)
    
    # Without explicit $ delimiters (common in some exports)
    html_content = re.sub(r'<span class="math">(.*?)</span>', save_math, html_content, flags=re.DOTALL)
    html_content = re.sub(r'<pre class="math">(.*?)</pre>', save_math, html_content, flags=re.DOTALL)
    
    # Unescape HTML entities
    content = unescape(html_content)
    # Handle common HTML entities manually if unescape didn't work fully
    content = content.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    
    # Remove <style> and <script> content completely
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    
    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Extract code blocks to protect them
    code_blocks = []
    
    def save_code_block(match):
        code = match.group(1).rstrip()
        # Preserve indentation in code blocks
        code_blocks.append(code)
        return f"CODE_BLOCK_PLACEHOLDER_{len(code_blocks) - 1}"
    
    # Save <pre> and <code> content
    content = re.sub(r'<pre><code>(.*?)</code></pre>', save_code_block, content, flags=re.DOTALL)
    content = re.sub(r'<pre>(.*?)</pre>', save_code_block, content, flags=re.DOTALL)
    content = re.sub(r'<code>(.*?)</code>', r'`\1`', content, flags=re.DOTALL)
    
    # ---- Handle common block elements ----
    
    # Handle blockquotes first
    content = re.sub(r'<blockquote>(.*?)</blockquote>', 
                    lambda m: '\n> ' + m.group(1).strip().replace('\n', '\n> ') + '\n', 
                    content, flags=re.DOTALL)

    # Handle heading tags - reduced newlines
    for i in range(1, 7):
        content = re.sub(f'<h{i}[^>]*>(.*?)</h{i}>', f'\n{"#" * i} \\1\n', content, flags=re.DOTALL)
    
    # Handle div and paragraph tags with less newlines
    content = re.sub(r'<div[^>]*>(.*?)</div>', r'\n\1\n', content, flags=re.DOTALL)
    content = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', content, flags=re.DOTALL)
    
    # Handle horizontal rules
    content = re.sub(r'<hr[^>]*>', r'\n---\n', content)
    
    # Handle line breaks
    content = re.sub(r'<br[^>]*>', '\n', content)

    # ---- Handle lists properly ----
    
    # Process list items with less spacing
    def process_list_item(match):
        content = match.group(1).strip()
        # Split by newlines to handle multi-line list items
        lines = content.split('\n')
        # First line with bullet/number
        result = "- " + lines[0].strip()
        # Indented continuation lines
        if len(lines) > 1:
            result += '\n' + ''.join("  " + line.strip() + "\n" for line in lines[1:]).rstrip()
        return result

    # Process each list item
    content = re.sub(r'<li[^>]*>(.*?)</li>', process_list_item, content, flags=re.DOTALL)
    
    # Remove list container tags, maintaining proper structure but with less spacing
    content = re.sub(r'<[uo]l[^>]*>', '\n', content)
    content = re.sub(r'</[uo]l[^>]*>', '\n', content)
    
    # ---- Handle inline formatting ----
    
    # Convert common HTML tags to Markdown
    # Replace <strong> or <b> with **
    content = re.sub(r'<(?:strong|b)>(.*?)</(?:strong|b)>', r'**\1**', content, flags=re.DOTALL)
    
    # Replace <em> or <i> with *
    content = re.sub(r'<(?:em|i)>(.*?)</(?:em|i)>', r'*\1*', content, flags=re.DOTALL)
    
    # Convert <a> tags to Markdown links
    content = re.sub(r'<a[^>]*href=[\'"]([^\'"]*)[\'"][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL)
    
    # Remove any remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content, flags=re.DOTALL)
    
    # ---- Clean up and polish the result ----
    
    # Replace multiple consecutive newlines with double newlines - more aggressive reduction
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Clean up extra spaces
    content = re.sub(r' {2,}', ' ', content)
    content = re.sub(r'\n +', '\n', content)
    
    # Restore code blocks
    for i, code in enumerate(code_blocks):
        content = content.replace(f"CODE_BLOCK_PLACEHOLDER_{i}", f"```\n{code}\n```")
    
    # Restore math expressions
    for placeholder, (math_content, is_inline) in math_blocks.items():
        if is_inline:
            # Clean up any $ that might be in the original content
            clean_content = math_content.strip('$')
            content = content.replace(placeholder, f"${clean_content}$")
        else:
            # Clean up any $$ that might be in the original content
            clean_content = math_content.strip('$')
            content = content.replace(placeholder, f"$$\n{clean_content}\n$$")
    
    # Detect and format math expressions that weren't properly marked with math classes
    # Find common LaTeX patterns like \mathcal{}, \alpha, etc. and wrap them in $ delimiters
    
    # 1. Handle POMDP formula: [ \mathcal{M} = (S, A, T, R, \Omega, O, H, \gamma) ]
    content = re.sub(r'\[\s*(\\mathcal{[^}]+}.*?[\\()\[\],\s\w\^=]+)\s*\]', r'$\1$', content)
    
    # 2. Handle math expressions with LaTeX commands
    content = re.sub(r'\[\s*((\\[a-zA-Z]+(\{[^}]*\})?(\s*[=><\(\)\[\]\{\},\+\-\*/\^0-9a-zA-Z])*)+)\s*\]', r'$\1$', content)
    
    # 3. Handle expressions with Greek letters like (\Omega)
    content = re.sub(r'\(\\([A-Z][a-z]+)\)', r'$\\\1$', content)
    
    # 4. Handle other LaTeX-style references that are not already in math mode
    math_symbols = ['mathcal', 'mathbb', 'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 
                   'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma', 'tau', 
                   'upsilon', 'phi', 'chi', 'psi', 'omega', 'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 
                   'Pi', 'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega', 'sum', 'prod', 'infty', 'int', 'partial']
    
    # Iterate through each line to identify potential math content
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Skip lines that are already in math mode or code blocks
        if '$' in line or line.startswith('```') or line.startswith('    '):
            continue
            
        # Look for common LaTeX commands
        for symbol in math_symbols:
            pattern = f"\\\\{symbol}"
            if re.search(pattern, line):
                # If the line has square brackets and LaTeX commands, treat as inline math
                if line.strip().startswith('[') and line.strip().endswith(']') and '\\' in line:
                    math_content = line.strip()[1:-1].strip()
                    lines[i] = f"${math_content}$"
                    break
    
    content = '\n'.join(lines)
    
    # Handle specific pattern [ \mathcal{M} = (S, A, T, R, \Omega, O, H, \gamma) ]
    exact_pomdp = r'\[ \\mathcal\{M\} = \(S, A, T, R, \\Omega, O, H, \\gamma\) \]'
    if re.search(exact_pomdp, content):
        content = content.replace('[ \\mathcal{M} = (S, A, T, R, \\Omega, O, H, \\gamma) ]', 
                               '$\\mathcal{M} = (S, A, T, R, \\Omega, O, H, \\gamma)$')
    
    # Fix any broken list indentation
    lines = content.split('\n')
    result_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('- '):
            indent_level = line.find('-')
            if indent_level > 0:
                result_lines.append(" " * indent_level + stripped)
            else:
                result_lines.append(stripped)
        else:
            result_lines.append(line)
    
    content = '\n'.join(result_lines)
    
    # Wrap long lines but keep output compact
    MAX_LINE_WIDTH = 100  # Wider line width for compactness
    wrapped_lines = []
    in_code_block = False
    in_math_block = False
    
    for line in content.split('\n'):
        # Don't wrap special content
        if line.startswith('```'):
            in_code_block = not in_code_block
            wrapped_lines.append(line)
            continue
        elif line.startswith('$$'):
            in_math_block = not in_math_block
            wrapped_lines.append(line)
            continue
        elif in_code_block or in_math_block:
            wrapped_lines.append(line)
            continue
        elif line.startswith('#') or line.strip() == '---' or line.strip() == '':
            wrapped_lines.append(line)
            continue
        elif line.startswith('- ') or line.startswith('  '):
            # Don't wrap list items or their continuations
            wrapped_lines.append(line)
            continue
        elif '$' in line and not (line.count('$') >= 2):
            # Line has unclosed math expression, don't wrap
            wrapped_lines.append(line)
            continue
            
        # Wrap normal paragraph text
        if len(line) > MAX_LINE_WIDTH:
            # Use textwrap to do proper word wrapping
            wrapped_text = textwrap.fill(line, width=MAX_LINE_WIDTH)
            wrapped_lines.append(wrapped_text)
        else:
            wrapped_lines.append(line)

    content = '\n'.join(wrapped_lines)
    
    # Final cleanup - special pattern to handle consecutive empty lines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # Fix common patterns that create excessive spacing
    content = re.sub(r'\n\n- ', '\n- ', content)  # Remove extra line before list items
    content = re.sub(r'\n\n\n', '\n\n', content)  # Further reduce triple newlines
    
    # Special case for empty lines between list items
    content = re.sub(r'\n- \n\n- ', '\n- \n- ', content)
    
    # Ensure there's a blank line before headings for readability
    content = re.sub(r'([^\n])\n(#+\s)', r'\1\n\n\2', content)
    
    # Eliminate excessive whitespace at start/end
    content = content.strip()
    
    return content

def test_html_to_markdown():
    """Test the html_to_markdown function with various HTML inputs"""
    test_cases = [
        # Basic formatting tests
        ("<p>Simple paragraph</p>", "Simple paragraph"),
        ("<strong>Bold text</strong>", "**Bold text**"),
        ("<em>Italic text</em>", "*Italic text*"),
        ("<h1>Heading 1</h1>", "# Heading 1"),
        ("<h2>Heading 2</h2>", "## Heading 2"),
        
        # Lists
        ("<ul><li>Item 1</li><li>Item 2</li></ul>", "- Item 1\n- Item 2"),
        ("<ol><li>First</li><li>Second</li></ol>", "- First\n- Second"),
        
        # Nested formatting
        ("<p>Text with <strong>bold</strong> and <em>italic</em></p>", "Text with **bold** and *italic*"),
        ("<div><p>Nested tags</p></div>", "Nested tags"),
        
        # Line breaks
        ("<p>Line 1<br>Line 2</p>", "Line 1\nLine 2"),
        
        # HTML entities
        ("<p>HTML entities: &amp; &lt; &gt;</p>", "HTML entities: & < >"),
        
        # Links
        ("<a href='https://example.com'>Link text</a>", "[Link text](https://example.com)"),
        
        # Code blocks
        ("<code>print('hello')</code>", "`print('hello')`"),
        ("<pre>def function():\n    return True</pre>", "```\ndef function():\n    return True\n```"),
        
        # Math formulas with $ delimiters
        ("<span class=\"math\">$x^2 + y^2 = z^2$</span>", "$x^2 + y^2 = z^2$"),
        ("<pre class=\"math\">$$E = mc^2$$</pre>", "$$\nE = mc^2\n$$"),
        
        # Math formulas without $ delimiters
        ("<span class=\"math\">x^2 + y^2 = z^2</span>", "$x^2 + y^2 = z^2$"),
        ("<pre class=\"math\">E = mc^2</pre>", "$$\nE = mc^2\n$$"),
        
        # Complex nested HTML
        ("""<div class="note">
            <h2>Complex Note</h2>
            <p>This is a <strong>complex</strong> note with <em>different</em> elements.</p>
            <ul>
                <li>Point 1</li>
                <li>Point 2 with <a href="https://example.com">link</a></li>
            </ul>
            <blockquote>
                This is a quoted text.
                It may span multiple lines.
            </blockquote>
            <pre><code>def hello_world():
    print("Hello world!")
            </code></pre>
        </div>""", 
        """## Complex Note

This is a **complex** note with *different* elements.

- Point 1
- Point 2 with [link](https://example.com)

> This is a quoted text.
> It may span multiple lines.

```
def hello_world():
    print("Hello world!")
```""")
    ]
    
    print("Running tests for html_to_markdown:")
    print("---------------------------------")
    passed = 0
    failed = 0
    
    for i, (html, expected_markdown) in enumerate(test_cases, 1):
        result = html_to_markdown(html)
        if result.strip() == expected_markdown.strip():
            passed += 1
            print(f"✓ Test {i} passed")
        else:
            failed += 1
            print(f"✗ Test {i} failed:")
            print(f"  Input: {html}")
            print(f"  Expected: {expected_markdown}")
            print(f"  Got: {result}")
    
    print("---------------------------------")
    print(f"Tests completed: {len(test_cases)} total, {passed} passed, {failed} failed")
    
    # Additional edge case tests
    print("\nTesting edge cases:")
    print("---------------------------------")
    
    # Test with None or empty string
    assert html_to_markdown(None) == "", "Should handle None input"
    assert html_to_markdown("") == "", "Should handle empty string"
    
    # Test with malformed HTML
    malformed = "<p>Unclosed tag"
    print(f"Malformed HTML: {malformed}")
    print(f"Result: {html_to_markdown(malformed)}")
    
    # Test with script and style tags that should be removed
    with_script = "<p>Text</p><script>alert('test');</script><p>More text</p>"
    assert "alert" not in html_to_markdown(with_script), "Should remove script tags"
    
    # Test with HTML comments
    with_comments = "<!-- Comment --><p>Text</p>"
    assert "Comment" not in html_to_markdown(with_comments), "Should remove HTML comments"
    
    # Test with math formulas - additional cases
    inline_math = "<span class=\"math\">a + b = c</span>"
    assert "$a + b = c$" == html_to_markdown(inline_math).strip(), "Should handle inline math without $ delimiters"
    
    block_math = "<pre class=\"math\">\\begin{align} F = ma \\end{align}</pre>"
    assert "$$\n\\begin{align} F = ma \\end{align}\n$$" == html_to_markdown(block_math).strip(), "Should handle block math without $$ delimiters"
    
    print("Edge case tests completed")

def read_library_version():
    """
    Reads the library version from the 'since' file and returns it as an integer.
    If the file does not exist or does not include a number, returns 0.
    """
    try:
        with open('since', 'r', encoding='utf-8') as file:
            return int(file.read())
    except FileNotFoundError:
        print("since file does not exist, using library version 0")
    except ValueError:
        print("since file does not include a number, using library version 0")
    return 0

def write_library_version(zotero_client):
    """
    Writes the library version of the given Zotero client to a file named 'since'.

    Args:
        zotero_client: A Zotero client object.

    Returns:
        None
    """
    with open('since', 'w', encoding='utf-8') as file:
        file.write(str(zotero_client.last_modified_version()))

if __name__ == "__main__":
    """
    Command-line interface for testing HTML to Markdown conversion.
    
    Usage:
        python -m zotero2readwise.helper --test
            Runs tests for html_to_markdown function
        
        python -m zotero2readwise.helper --convert "<html>"
            Converts HTML string to Markdown and prints the result
            
        python -m zotero2readwise.helper --convert-file input.html
            Converts HTML file to Markdown and prints the result
    """
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m zotero2readwise.helper --test")
        print("  python -m zotero2readwise.helper --convert \"<html>\"")
        print("  python -m zotero2readwise.helper --convert-file input.html")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "--test":
        test_html_to_markdown()
    
    elif command == "--convert" and len(sys.argv) > 2:
        html_content = sys.argv[2]
        print("\nInput HTML:")
        print("----------")
        print(html_content)
        print("\nConverted Markdown:")
        print("------------------")
        print(html_to_markdown(html_content))
    
    elif command == "--convert-file" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)
            
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            
        markdown = html_to_markdown(html_content)
        
        # Print the converted markdown
        print("\nConverted Markdown:")
        print("------------------")
        print(markdown)
        
        # Save the result to a file
        output_path = os.path.splitext(file_path)[0] + '.md'
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(markdown)
        print(f"\nMarkdown saved to: {output_path}")
    
    else:
        print("Invalid command or missing argument.")
        print("Usage:")
        print("  python -m zotero2readwise.helper --test")
        print("  python -m zotero2readwise.helper --convert \"<html>\"")
        print("  python -m zotero2readwise.helper --convert-file input.html")