/**
 * Clean Tiptap Editor Implementation
 * Simple, working rich text editor with placeholder and table functionality
 */

class TiptapEditor {
    constructor(textareaId, options = {}) {
        this.textareaId = textareaId;
        this.textarea = document.getElementById(textareaId);
        this.options = {
            placeholder: 'Enter notes for this subject...',
            ...options
        };
        
        if (!this.textarea) {
            console.error(`Textarea with id "${textareaId}" not found`);
            return;
        }
        
        this.init();
    }
    
    init() {
        this.createWrapper();
        this.createToolbar();
        this.createEditor();
        this.setupEventListeners();
        this.loadContent();
    }
    
    createWrapper() {
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'tiptap-wrapper';
        this.wrapper.style.cssText = `
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
            margin: 10px 0;
        `;
        
        this.textarea.parentNode.insertBefore(this.wrapper, this.textarea);
        this.textarea.style.display = 'none';
    }
    
    createToolbar() {
        this.toolbar = document.createElement('div');
        this.toolbar.className = 'tiptap-toolbar';
        this.toolbar.style.cssText = `
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            padding: 10px;
            border-bottom: 1px solid #eee;
            background: #f8f9fa;
        `;
        
        this.wrapper.appendChild(this.toolbar);
        this.buttons = []; // Store button references for state management
        this.createToolbarButtons();
    }
    
    createToolbarButtons() {
        const buttons = [
            { cmd: 'bold', label: 'B', title: 'Bold', style: 'font-weight: bold;' },
            { cmd: 'italic', label: 'I', title: 'Italic', style: 'font-style: italic;' },
            { cmd: 'underline', label: 'U', title: 'Underline', style: 'text-decoration: underline;' },
            { cmd: 'insertUnorderedList', label: '•', title: 'Bullet List' },
            { cmd: 'insertOrderedList', label: '1.', title: 'Numbered List' },
            { cmd: 'insertTaskList', label: '☐', title: 'Task List' },
            { cmd: 'formatBlock', label: 'H2', title: 'Heading 2', value: 'h2' },
            { cmd: 'insertBlockquote', label: 'Quote', title: 'Quote' },
            { cmd: 'insertHorizontalRule', label: 'Line', title: 'Horizontal Line' },
            { cmd: 'insertTable', label: 'Table', title: 'Insert Table' },
            { cmd: 'addRow', label: '+R', title: 'Add Row' },
            { cmd: 'addColumn', label: '+C', title: 'Add Column' },
            { cmd: 'deleteRow', label: '-R', title: 'Delete Row' },
            { cmd: 'deleteColumn', label: '-C', title: 'Delete Column' },
            { cmd: 'deleteTable', label: '🗑️', title: 'Delete Table' }
        ];
        
        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'toolbar-btn';
            button.innerHTML = btn.label;
            button.title = btn.title;
            button.dataset.cmd = btn.cmd;
            button.dataset.value = btn.value || '';
            button.style.cssText = `
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                color: #333;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                transition: all 0.2s ease;
                ${btn.style || ''}
            `;
            
            button.addEventListener('mouseenter', () => {
                if (!button.classList.contains('active')) {
                    button.style.backgroundColor = '#e9ecef';
                }
            });
            
            button.addEventListener('mouseleave', () => {
                if (!button.classList.contains('active')) {
                    button.style.backgroundColor = 'white';
                }
            });
            
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.editor.focus();
                
                if (btn.cmd === 'insertTable') {
                    this.insertTable();
                } else if (btn.cmd === 'insertTaskList') {
                    this.insertTaskList();
                } else if (btn.cmd === 'bold') {
                    this.toggleBold();
                } else if (btn.cmd === 'italic') {
                    this.toggleItalic();
                } else if (btn.cmd === 'underline') {
                    this.toggleUnderline();
                } else if (btn.cmd === 'insertBlockquote') {
                    this.toggleBlockquote();
                } else if (btn.cmd === 'formatBlock') {
                    document.execCommand('formatBlock', false, btn.value);
                } else if (btn.cmd === 'addRow') {
                    console.log('➕ Add Row button clicked');
                    this.addTableRow();
                } else if (btn.cmd === 'addColumn') {
                    console.log('➕ Add Column button clicked');
                    this.addTableColumn();
                } else if (btn.cmd === 'deleteRow') {
                    console.log('🗑️ Delete Row button clicked');
                    this.deleteTableRow();
                } else if (btn.cmd === 'deleteColumn') {
                    console.log('🗑️ Delete Column button clicked');
                    this.deleteTableColumn();
                } else if (btn.cmd === 'deleteTable') {
                    this.deleteTable();
                } else {
                    document.execCommand(btn.cmd, false, null);
                }
                
                this.syncToTextarea();
                this.updateButtonStates();
            });
            
            this.buttons.push(button);
            this.toolbar.appendChild(button);
        });
    }
    
    createEditor() {
        this.editor = document.createElement('div');
        this.editor.className = 'tiptap-editor';
        this.editor.contentEditable = true;
        this.editor.style.cssText = `
            min-height: 200px;
            padding: 20px;
            outline: none;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            position: relative;
        `;
        
        this.wrapper.appendChild(this.editor);
        
        // Add placeholder styling
        this.addPlaceholderStyles();
    }
    
    addPlaceholderStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .tiptap-editor:empty:before {
                content: "${this.options.placeholder}";
                color: #999;
                font-style: italic;
                pointer-events: none;
                position: absolute;
                top: 20px;
                left: 20px;
            }
            
            .tiptap-editor table {
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                border: 1px solid #ddd;
            }
            
            .tiptap-editor th,
            .tiptap-editor td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
                vertical-align: top;
                min-width: 50px;
            }
            
            .tiptap-editor th {
                background: #f2f2f2;
                font-weight: bold;
            }
            
            .tiptap-editor ul,
            .tiptap-editor ol {
                padding-left: 20px;
            }
            
            .tiptap-editor li {
                margin: 4px 0;
            }
            
            .tiptap-editor blockquote {
                margin: 10px 0;
                padding: 10px 20px;
                background: #f8f9fa;
                font-style: italic;
            }
            
            .tiptap-editor hr {
                border: none;
                border-top: 1px solid #ccc;
                margin: 20px 0;
                background: none;
                height: 1px;
            }
            
            /* Checklist styling */
            .tiptap-editor .checklist-item {
                margin: 4px 0;
                padding: 2px 0;
                cursor: text;
            }
            
            .tiptap-editor .checklist-item input[type="checkbox"] {
                margin-right: 8px;
                cursor: pointer;
            }
            
            /* Active button states */
            .toolbar-btn.active {
                background: #495057 !important;
                color: white !important;
                border-color: #343a40 !important;
                box-shadow: 0 2px 4px rgba(73, 80, 87, 0.3);
            }
            
            .toolbar-btn.active:hover {
                background: #343a40 !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        // Sync content to textarea and trigger auto-save
        this.editor.addEventListener('input', () => {
            this.updateChecklistEmptyStates();
            this.syncToTextarea();
            this.updateButtonStates();
            this.triggerAutoSave();
        });
        
        // Handle paste
        this.editor.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
            this.updateButtonStates();
            this.triggerAutoSave();
        });
        
        // Position cursor at top-left on click (only when editor is empty)
        this.editor.addEventListener('click', (e) => {
            this.handleEditorClick(e);
            this.updateButtonStates();
        });
        
        // Update button states on selection change
        this.editor.addEventListener('selectionchange', () => {
            this.updateButtonStates();
        });
        
        // Also update on focus to catch cursor positioning
        this.editor.addEventListener('focus', () => {
            setTimeout(() => this.updateButtonStates(), 10);
        });
        
        // Update button states on keyup (for keyboard navigation)
        this.editor.addEventListener('keyup', () => {
            this.updateButtonStates();
        });
        
        // Handle Enter key for checklist continuation and Backspace for deletion
        this.editor.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.handleEnterKey(e);
            } else if (e.key === 'Backspace') {
                this.handleBackspaceKey(e);
            }
        });
    }
    
    handleEditorClick(e) {
        // Only position cursor at top-left if:
        // 1. Editor is completely empty (no content)
        // 2. Click is not inside a table cell
        // 3. Click is not inside any existing content
        
        const clickedElement = e.target;
        const isInTable = clickedElement.closest('td, th, table');
        const hasContent = this.editor.textContent.trim().length > 0;
        
        // If clicking in a table cell, let the browser handle normal cursor positioning
        if (isInTable) {
            return;
        }
        
        // If editor has content, let the browser handle normal cursor positioning
        if (hasContent) {
            return;
        }
        
        // Only position at top-left if editor is truly empty
        this.positionCursorAtTopLeft();
    }
    
    
    positionCursorAtTopLeft() {
        setTimeout(() => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                
                // Only move cursor if it's not already at the beginning
                if (range.startOffset > 0) {
                    const newRange = document.createRange();
                    newRange.setStart(this.editor, 0);
                    newRange.collapse(true);
                    
                    selection.removeAllRanges();
                    selection.addRange(newRange);
                }
            }
        }, 10);
    }
    
    updateButtonStates() {
        // Reset all buttons
        this.buttons.forEach(button => {
            button.classList.remove('active');
            button.style.backgroundColor = 'white';
            button.style.color = '#333';
        });
        
        // Check if cursor is in a checklist item
        const selection = window.getSelection();
        let isInChecklist = false;
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const container = range.startContainer;
            
            // Check if startContainer itself is a checklist item OR if its parent is
            const checklistItem = container.classList?.contains('checklist-item') 
                ? container 
                : container.parentElement?.closest('.checklist-item');
            
            isInChecklist = !!checklistItem;
            
        }
        
        // Check formatting states
        this.buttons.forEach(button => {
            const cmd = button.dataset.cmd;
            const value = button.dataset.value;
            
            try {
                if (cmd === 'bold' && document.queryCommandState('bold')) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'italic' && document.queryCommandState('italic')) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'underline' && document.queryCommandState('underline')) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'insertUnorderedList' && document.queryCommandState('insertUnorderedList')) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'insertOrderedList' && document.queryCommandState('insertOrderedList')) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'insertTaskList' && isInChecklist) {
                    button.classList.add('active');
                    button.style.backgroundColor = '#495057';
                    button.style.color = 'white';
                } else if (cmd === 'insertBlockquote') {
                    // Check if cursor is in a blockquote
                    const selection = window.getSelection();
                    if (selection.rangeCount > 0) {
                        const range = selection.getRangeAt(0);
                        const container = range.startContainer;
                        
                        // Check multiple possible containers for blockquote
                        let blockquote = null;
                        
                        // First try: direct closest check
                        if (container.closest) {
                            blockquote = container.closest('blockquote');
                        }
                        
                        // Second try: check parent element
                        if (!blockquote && container.parentElement) {
                            blockquote = container.parentElement.closest('blockquote');
                        }
                        
                        // Third try: check if container itself is blockquote
                        if (!blockquote && container.nodeType === Node.ELEMENT_NODE && container.tagName === 'BLOCKQUOTE') {
                            blockquote = container;
                        }
                        
                        // Fourth try: check if container is inside blockquote by traversing up
                        if (!blockquote) {
                            let currentElement = container;
                            while (currentElement && currentElement !== this.editor) {
                                if (currentElement.nodeType === Node.ELEMENT_NODE && currentElement.tagName === 'BLOCKQUOTE') {
                                    blockquote = currentElement;
                                    break;
                                }
                                currentElement = currentElement.parentNode;
                            }
                        }
                        
                        if (blockquote) {
                            button.classList.add('active');
                            button.style.backgroundColor = '#495057';
                            button.style.color = 'white';
                        }
                    }
                } else if (cmd === 'formatBlock') {
                    // Check if current block format matches button value
                    const currentFormat = document.queryCommandValue('formatBlock');
                    if (currentFormat === value) {
                        button.classList.add('active');
                        button.style.backgroundColor = '#495057';
                        button.style.color = 'white';
                    }
                }
            } catch (error) {
                console.log('⚠️ Error checking command state for:', cmd, error);
            }
        });
    }
    
    insertTable() {
        // Default to 2 rows (1 header + 1 data row) and 2 columns
        const rows = 2;
        const cols = 2;
        
        const table = document.createElement('table');
            table.style.cssText = `
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                border: 1px solid #ddd;
            `;
            
            for (let i = 0; i < parseInt(rows); i++) {
                const row = document.createElement('tr');
                
                for (let j = 0; j < parseInt(cols); j++) {
                    let cell;
                    if (i === 0) {
                        // Create header cell for first row
                        cell = document.createElement('th');
                        cell.style.cssText = `
                            border: 1px solid #ddd;
                            padding: 8px;
                            background: #f2f2f2;
                            font-weight: bold;
                            text-align: left;
                            vertical-align: top;
                        `;
                    } else {
                        // Create data cell for other rows
                        cell = document.createElement('td');
                        cell.style.cssText = `
                            border: 1px solid #ddd;
                            padding: 8px;
                            background: white;
                            text-align: left;
                            vertical-align: top;
                        `;
                    }
                    
                    cell.innerHTML = '<br>';
                    cell.contentEditable = true;
                    row.appendChild(cell);
                }
                
                table.appendChild(row);
            }
            
            // Insert table at cursor position
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                range.insertNode(table);
                
                // Position cursor after table
                range.setStartAfter(table);
                range.collapse(true);
                selection.removeAllRanges();
                selection.addRange(range);
            } else {
                this.editor.appendChild(table);
            }
            
            this.syncToTextarea();
    }
    
    insertTaskList() {
        // Create a clean checklist item
        const newChecklistItem = document.createElement('div');
        newChecklistItem.className = 'checklist-item';
        newChecklistItem.contentEditable = true;
        newChecklistItem.setAttribute('data-empty', 'true');
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.style.marginRight = '8px';
        
        newChecklistItem.appendChild(checkbox);
        
        // Insert at cursor position
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.insertNode(newChecklistItem);
            
            // Position cursor after the checkbox in the newly created checklist item
            const newRange = document.createRange();
            
            // Position cursor at the end of the checklist item (after checkbox)
            newRange.setStart(newChecklistItem, newChecklistItem.childNodes.length);
            newRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(newRange);
            
            // Focus the editor to ensure cursor is visible
            this.editor.focus();
        } else {
            this.editor.appendChild(newChecklistItem);
            
            // Position cursor in the checklist item
            const newRange = document.createRange();
            newRange.setStart(newChecklistItem, newChecklistItem.childNodes.length);
            newRange.collapse(true);
            selection.removeAllRanges();
            selection.addRange(newRange);
            this.editor.focus();
        }
        
        this.syncToTextarea();
        
        // Update button states immediately after creating checklist
        setTimeout(() => {
            this.updateButtonStates();
        }, 10);
    }
    
    handleEnterKey(e) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return;
        
        const range = selection.getRangeAt(0);
        const container = range.startContainer;
        
        // Check if we're in a checklist item
        const currentElement = container.classList?.contains('checklist-item') 
            ? container 
            : container.parentElement?.closest('.checklist-item');
        
        if (currentElement) {
            // Prevent default behavior for checklist items
            e.preventDefault();
            e.stopPropagation();
            // Check if this is truly an empty checklist item (only contains checkbox)
            // Look for actual text nodes with content (excluding whitespace)
            const textNodes = Array.from(currentElement.childNodes).filter(node => 
                node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
            );
            const hasUserText = textNodes.length > 0;
            const isEmpty = !hasUserText;
            
            
            
            if (isEmpty) {
                // Empty checklist item - exit checklist mode (like bullet lists)
                // Remove ONLY the current empty checklist item
                const parent = currentElement.parentNode;
                const nextSibling = currentElement.nextSibling;
                
                // Remove the empty checklist item
                currentElement.remove();
                
                // Create normal paragraph
                const newP = document.createElement('p');
                newP.innerHTML = '<br>';
                
                // Insert where the empty checklist item was
                if (nextSibling) {
                    parent.insertBefore(newP, nextSibling);
                } else {
                    parent.appendChild(newP);
                }
                
                // Position cursor in new paragraph
                const newRange = document.createRange();
                newRange.setStart(newP, 0);
                newRange.collapse(true);
                selection.removeAllRanges();
                selection.addRange(newRange);
                
                this.syncToTextarea();
                this.updateButtonStates(); // Update button states when exiting checklist
            } else {
                // Has text - create new checklist item
                this.createNewChecklistItem(currentElement, selection);
            }
        }
        // For other elements, let browser handle naturally
    }
    
    handleBackspaceKey(e) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return;
        
        const range = selection.getRangeAt(0);
        const container = range.startContainer;
        
        // Check if we're in a checklist item
        const currentElement = container.classList?.contains('checklist-item') 
            ? container 
            : container.parentElement?.closest('.checklist-item');
        
        if (currentElement) {
            // Check if cursor is at the beginning of the checklist item (after checkbox)
            const isAtStart = range.startOffset === 1 && range.startContainer === currentElement;
            
            if (isAtStart) {
                // Cursor is right after checkbox - delete the checklist item
                e.preventDefault();
                
                // Store reference to previous sibling before removing
                const previousSibling = currentElement.previousSibling;
                const parent = currentElement.parentNode;
                
                // Remove the checklist item
                currentElement.remove();
                
                // If there was a previous sibling, position cursor at the end of it
                if (previousSibling) {
                    const newRange = document.createRange();
                    newRange.selectNodeContents(previousSibling);
                    newRange.collapse(false); // Collapse to end
                    selection.removeAllRanges();
                    selection.addRange(newRange);
                } else {
                    // No previous sibling - create a normal paragraph
                    const newP = document.createElement('p');
                    newP.innerHTML = '<br>';
                    parent.insertBefore(newP, parent.firstChild);
                    
                    const newRange = document.createRange();
                    newRange.setStart(newP, 0);
                    newRange.collapse(true);
                    selection.removeAllRanges();
                    selection.addRange(newRange);
                }
                
                this.syncToTextarea();
                this.updateButtonStates();
            }
        }
        // For other elements, let browser handle naturally
    }
    
    createNewChecklistItem(currentElement, selection) {
        // Helper function to create a new checklist item after the current one
        // Create a simple, clean checklist item
        const newChecklistItem = document.createElement('div');
        newChecklistItem.className = 'checklist-item';
        newChecklistItem.contentEditable = true;
        newChecklistItem.setAttribute('data-empty', 'true');
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.style.marginRight = '8px';
        
        newChecklistItem.appendChild(checkbox);
        
        // Insert after current checklist item
        currentElement.parentNode.insertBefore(newChecklistItem, currentElement.nextSibling);
        
        // Position cursor in new checklist item
        const newRange = document.createRange();
        
        // Position cursor at the end of the checklist item (after checkbox)
        newRange.setStart(newChecklistItem, newChecklistItem.childNodes.length);
        newRange.collapse(true);
        selection.removeAllRanges();
        selection.addRange(newRange);
        
        this.syncToTextarea();
        this.updateButtonStates();
    }
    
    updateChecklistEmptyStates() {
        // Update data-empty attribute for all checklist items
        const checklistItems = this.editor.querySelectorAll('.checklist-item');
        checklistItems.forEach(item => {
            const textNodes = Array.from(item.childNodes).filter(node => 
                node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0
            );
            const hasText = textNodes.length > 0;
            
            if (hasText) {
                item.removeAttribute('data-empty');
            } else {
                item.setAttribute('data-empty', 'true');
            }
        });
    }
    
    toggleBold() {
        // Simple toggle - just use execCommand
        document.execCommand('bold', false, null);
        this.syncToTextarea();
    }
    
    toggleItalic() {
        // Simple toggle - just use execCommand
        document.execCommand('italic', false, null);
        this.syncToTextarea();
    }
    
    toggleUnderline() {
        // Simple toggle - just use execCommand
        document.execCommand('underline', false, null);
        this.syncToTextarea();
    }
    
    toggleBlockquote() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const container = range.startContainer;
            
            // Enhanced blockquote detection
            let blockquote = null;
            if (container.closest) {
                blockquote = container.closest('blockquote');
            } else if (container.parentElement) {
                blockquote = container.parentElement.closest('blockquote');
            } else if (container.nodeType === Node.ELEMENT_NODE && container.tagName === 'BLOCKQUOTE') {
                blockquote = container;
            }
            
            if (blockquote) {
                // Already in blockquote - exit quote mode and move to new line
                // Create a new paragraph element
                const newP = document.createElement('p');
                newP.innerHTML = '<br>';
                
                // Insert the new paragraph after the blockquote
                if (blockquote.nextSibling) {
                    blockquote.parentNode.insertBefore(newP, blockquote.nextSibling);
                } else {
                    blockquote.parentNode.appendChild(newP);
                }
                
                // Position cursor in the new paragraph
                const newRange = document.createRange();
                newRange.setStart(newP, 0);
                newRange.collapse(true);
                selection.removeAllRanges();
                selection.addRange(newRange);
                
                // Focus the editor
                this.editor.focus();
            } else {
                // Not in blockquote - create one
                document.execCommand('formatBlock', false, 'blockquote');
            }
            
            // Update button states and sync
            setTimeout(() => {
                this.updateButtonStates();
                this.syncToTextarea();
            }, 10);
        }
    }
    
    addTableRow() {
        console.log('🔧 Add Table Row clicked');
        const selection = window.getSelection();
        console.log('Selection range count:', selection.rangeCount);
        
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            console.log('Range start container:', range.startContainer);
            
            // Improved cell detection - handle text nodes
            let cell = null;
            if (range.startContainer.closest) {
                cell = range.startContainer.closest('td, th');
            } else if (range.startContainer.parentElement) {
                cell = range.startContainer.parentElement.closest('td, th');
            } else if (range.startContainer.nodeType === Node.ELEMENT_NODE && 
                      (range.startContainer.tagName === 'TD' || range.startContainer.tagName === 'TH')) {
                cell = range.startContainer;
            }
            
            console.log('Found cell:', cell);
            
            if (cell) {
                const row = cell.closest('tr');
                const table = cell.closest('table');
                const newRow = document.createElement('tr');
                
                // Count columns in the table
                const columnCount = table.rows[0].cells.length;
                
                for (let i = 0; i < columnCount; i++) {
                    // Always create data cells (td) for new rows, not header cells (th)
                    // Only the first row should have header cells
                    const newCell = document.createElement('td');
                    newCell.style.cssText = `
                        border: 1px solid #ddd;
                        padding: 8px;
                        background: white;
                        font-weight: normal;
                        text-align: left;
                        vertical-align: top;
                    `;
                    newCell.innerHTML = '<br>';
                    newCell.contentEditable = true;
                    newRow.appendChild(newCell);
                }
                
                // Insert after current row
                row.parentNode.insertBefore(newRow, row.nextSibling);
                this.syncToTextarea();
                this.triggerAutoSave();
            }
        }
    }
    
    addTableColumn() {
        console.log('🔧 Add Table Column clicked');
        const selection = window.getSelection();
        console.log('Selection range count:', selection.rangeCount);
        
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            console.log('Range start container:', range.startContainer);
            
            // Improved cell detection - handle text nodes
            let cell = null;
            if (range.startContainer.closest) {
                cell = range.startContainer.closest('td, th');
            } else if (range.startContainer.parentElement) {
                cell = range.startContainer.parentElement.closest('td, th');
            } else if (range.startContainer.nodeType === Node.ELEMENT_NODE && 
                      (range.startContainer.tagName === 'TD' || range.startContainer.tagName === 'TH')) {
                cell = range.startContainer;
            }
            
            console.log('Found cell:', cell);
            
            if (cell) {
                const table = cell.closest('table');
                const columnIndex = Array.from(cell.parentNode.cells).indexOf(cell);
                
                // Add cell to each row
                for (let i = 0; i < table.rows.length; i++) {
                    const cellType = i === 0 ? 'th' : 'td'; // First row is headers
                    const newCell = document.createElement(cellType);
                    newCell.style.cssText = `
                        border: 1px solid #ddd;
                        padding: 8px;
                        background: ${cellType === 'th' ? '#f2f2f2' : 'white'};
                        font-weight: ${cellType === 'th' ? 'bold' : 'normal'};
                        text-align: left;
                        vertical-align: top;
                    `;
                    newCell.innerHTML = '<br>';
                    newCell.contentEditable = true;
                    
                    // Insert at the same column position in each row
                    if (columnIndex < table.rows[i].cells.length) {
                        table.rows[i].insertBefore(newCell, table.rows[i].cells[columnIndex + 1]);
                    } else {
                        table.rows[i].appendChild(newCell);
                    }
                }
                
                this.syncToTextarea();
                this.triggerAutoSave();
            }
        }
    }
    
    deleteTableRow() {
        console.log('🗑️ Delete Table Row clicked');
        const selection = window.getSelection();
        console.log('Selection range count:', selection.rangeCount);
        
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            console.log('Range start container:', range.startContainer);
            
            // Improved cell detection - handle text nodes
            let cell = null;
            if (range.startContainer.closest) {
                cell = range.startContainer.closest('td, th');
            } else if (range.startContainer.parentElement) {
                cell = range.startContainer.parentElement.closest('td, th');
            } else if (range.startContainer.nodeType === Node.ELEMENT_NODE && 
                      (range.startContainer.tagName === 'TD' || range.startContainer.tagName === 'TH')) {
                cell = range.startContainer;
            }
            
            console.log('Found cell:', cell);
            
            if (cell) {
                const row = cell.closest('tr');
                const table = cell.closest('table');
                
                // Don't delete if it's the only row
                if (table.rows.length > 1) {
                    row.remove();
                    this.syncToTextarea();
                    this.triggerAutoSave();
                }
            }
        }
    }
    
    deleteTableColumn() {
        console.log('🗑️ Delete Table Column clicked');
        const selection = window.getSelection();
        console.log('Selection range count:', selection.rangeCount);
        
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            console.log('Range start container:', range.startContainer);
            
            // Improved cell detection - handle text nodes
            let cell = null;
            if (range.startContainer.closest) {
                cell = range.startContainer.closest('td, th');
            } else if (range.startContainer.parentElement) {
                cell = range.startContainer.parentElement.closest('td, th');
            } else if (range.startContainer.nodeType === Node.ELEMENT_NODE && 
                      (range.startContainer.tagName === 'TD' || range.startContainer.tagName === 'TH')) {
                cell = range.startContainer;
            }
            
            console.log('Found cell:', cell);
            
            if (cell) {
                const table = cell.closest('table');
                const columnIndex = Array.from(cell.parentNode.cells).indexOf(cell);
                
                // Don't delete if it's the only column
                if (table.rows[0].cells.length > 1) {
                    // Remove cell from each row
                    for (let i = 0; i < table.rows.length; i++) {
                        if (table.rows[i].cells[columnIndex]) {
                            table.rows[i].deleteCell(columnIndex);
                        }
                    }
                    this.syncToTextarea();
                    this.triggerAutoSave();
                }
            }
        }
    }
    
    deleteTable() {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const cell = range.startContainer.closest('td, th');
            
            if (cell) {
                const table = cell.closest('table');
                
                // Confirm deletion
                if (confirm('Are you sure you want to delete this entire table?')) {
                    // Position cursor after the table
                    const range = document.createRange();
                    range.setStartAfter(table);
                    range.collapse(true);
                    
                    // Remove the table
                    table.remove();
                    
                    // Set cursor position after table deletion
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    this.syncToTextarea();
                    this.triggerAutoSave();
                    console.log('🗑️ Table deleted');
                }
            }
        }
    }
    
    loadContent() {
        if (this.textarea.value) {
            this.editor.innerHTML = this.textarea.value;
        }
        // Update button states after loading content
        setTimeout(() => {
            this.updateButtonStates();
        }, 100);
    }
    
    syncToTextarea() {
        this.textarea.value = this.editor.innerHTML;
    }
    
    triggerAutoSave() {
        // Find the form that contains this textarea
        const form = this.textarea.closest('form');
        if (!form) {
            console.log('❌ No form found for textarea:', this.textareaId);
            return;
        }
        
        // Find the subject ID input
        const subjectIdInput = form.querySelector('input[name="subject_id"]');
        if (!subjectIdInput) {
            console.log('❌ No subject ID input found in form');
            return;
        }
        
        
        // Trigger auto-save by dispatching an input event on the textarea
        // This will trigger the existing auto-save mechanism in today.html
        const event = new Event('input', { bubbles: true });
        this.textarea.dispatchEvent(event);
    }
}

// Auto-initialize on textareas with notes-textarea and important-notes-textarea classes
document.addEventListener('DOMContentLoaded', function() {
    // Initialize regular notes textareas
    const notesTextareas = document.querySelectorAll('textarea.notes-textarea');
    notesTextareas.forEach(textarea => {
        if (!textarea.previousElementSibling?.classList.contains('tiptap-wrapper')) {
            new TiptapEditor(textarea.id, {
                placeholder: textarea.placeholder || 'Enter notes for this subject...'
            });
        }
    });
    
    // Initialize important notes textareas
    const importantNotesTextareas = document.querySelectorAll('textarea.important-notes-textarea');
    importantNotesTextareas.forEach(textarea => {
        if (!textarea.previousElementSibling?.classList.contains('tiptap-wrapper')) {
            new TiptapEditor(textarea.id, {
                placeholder: textarea.placeholder || 'Enter any important notes for this subject...'
            });
        }
    });
    
    // Initialize mobile important notes textareas
    const mobileImportantTextareas = document.querySelectorAll('textarea.mobile-important-textarea');
    mobileImportantTextareas.forEach(textarea => {
        if (!textarea.previousElementSibling?.classList.contains('tiptap-wrapper')) {
            new TiptapEditor(textarea.id, {
                placeholder: textarea.placeholder || 'Important notes...'
            });
        }
    });
});

// Function to initialize editor for dynamically added textareas
window.initRichTextEditor = function(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (textarea && !textarea.previousElementSibling?.classList.contains('tiptap-wrapper')) {
        new TiptapEditor(textareaId, {
            placeholder: textareaId.includes('important_notes') ? 
                'Enter any important notes for this subject...' : 
                'Enter notes for this subject...'
        });
    }
};
