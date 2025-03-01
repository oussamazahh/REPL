let pyodide;
let editor;

async function initializePyodide() {
    pyodide = await loadPyodide();
    await pyodide.loadPackage('micropip');
    pyodide.runPython(`
        import sys
        from io import StringIO
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        def print_output():
            output = sys.stdout.getvalue() + sys.stderr.getvalue()
            sys.stdout.seek(0)
            sys.stdout.truncate(0)
            sys.stderr.seek(0)
            sys.stderr.truncate(0)
            return output
    `);
}

function initializeEditor() {
    editor = CodeMirror(document.getElementById('editor'), {
        lineNumbers: true,
        mode: 'python',
        theme: 'default',
        value: 'print("Hello, World!")',
        extraKeys: {"Ctrl-Enter": runCode},
        indentUnit: 4,
        matchBrackets: true,
        autoCloseBrackets: true,
    });
}

async function runCode() {
    const code = editor.getValue();
    const language = document.getElementById('language-selector').value;
    let output = '';

    if (language === 'python') {
        try {
            pyodide.runPython(code);
            output = pyodide.runPython('print_output()');
        } catch (e) {
            output = e.message;
        }
    } else {
        const response = await fetch('/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, language })
        });
        const data = await response.json();
        output = data.output;
    }

    const outputElement = document.getElementById('output');
    outputElement.textContent = output;
    outputElement.scrollTop = outputElement.scrollHeight;
}

document.addEventListener('DOMContentLoaded', async () => {
    await initializePyodide();
    initializeEditor();
    loadScripts();

    document.getElementById('run-btn').addEventListener('click', runCode);
    
    document.getElementById('save-btn').addEventListener('click', async () => {
        const title = prompt('Script title:');
        if (title) {
            const code = editor.getValue();
            const language = document.getElementById('language-selector').value;
            const response = await fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, code, language })
            });
            if (response.ok) loadScripts();
        }
    });

    document.getElementById('language-selector').addEventListener('change', (e) => {
        editor.setOption('mode', e.target.value === 'python' ? 'python' : 'javascript');
    });
});

async function loadScripts() {
    const response = await fetch('/scripts');
    const scripts = await response.json();
    const list = document.getElementById('script-list');
    list.innerHTML = '';
    scripts.forEach(script => {
        const li = document.createElement('li');
        li.textContent = script.title;
        li.onclick = () => {
            editor.setValue(script.code);
            document.getElementById('language-selector').value = script.language;
            editor.setOption('mode', script.language === 'python' ? 'python' : 'javascript');
        };
        list.appendChild(li);
    });
}

async function loadScripts() {
    const response = await fetch('/scripts');
    const scripts = await response.json();
    const list = document.getElementById('script-list');
    list.innerHTML = '';
    scripts.forEach(script => {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="script-item">
                <span>${script.title}</span>
                <div class="script-actions">
                    <button class="delete-btn" data-id="${script.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        li.querySelector('.delete-btn').addEventListener('click', async (e) => {
            if (confirm('Delete this script?')) {
                const scriptId = e.currentTarget.dataset.id;
                const response = await fetch(`/delete/${scriptId}`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    li.remove();
                }
            }
        });
        li.querySelector('span').onclick = () => {
            editor.setValue(script.code);
            document.getElementById('language-selector').value = script.language;
            editor.setOption('mode', script.language === 'python' ? 'python' : 'javascript');
        };
        list.appendChild(li);
    });
}

// Authentication check
fetch('/').catch(() => window.location.href = '/login');