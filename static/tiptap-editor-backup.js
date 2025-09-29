/**
 * Simple Tiptap-based Rich Text Editor
 * Replaces the custom rich-text-editor.js with proper table support
 */

class TiptapEditor {
    constructor(textareaId, options = {}) {
        this.textareaId = textareaId;
        this.textarea = document.getElementById(textareaId);
        this.currentTableCell = null;
        this.lastSpacingSelection = null;
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
        // Create the editor container
        this.createEditorContainer();
        
        // Initialize Tiptap
        this.initTiptap();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    createEditorContainer() {
        // Create wrapper
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'tiptap-wrapper';
        this.wrapper.style.cssText = `
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 5px 0;
            background: white;
        `;
        
        // Create toolbar
        this.toolbar = document.createElement('div');
        this.toolbar.className = 'tiptap-toolbar';
        this.toolbar.style.cssText = `
            border-bottom: 1px solid #ddd;
            padding: 8px;
            background: #f8f9fa;
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        `;
        
        // Create editor
        this.editorElement = document.createElement('div');
        this.editorElement.className = 'tiptap-editor';
        this.editorElement.style.cssText = `
            min-height: 300px;
            padding: 20px;
            outline: none;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            margin: 10px 0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            background: white;
        `;
        
        // Create placeholder element
        this.placeholderElement = document.createElement('div');
        this.placeholderElement.className = 'tiptap-placeholder';
        this.placeholderElement.textContent = this.options.placeholder;
        this.placeholderElement.style.cssText = `
            position: absolute;
            top: 8px;
            left: 8px;
            color: #999;
            font-style: italic;
            pointer-events: none;
            z-index: 1;
            user-select: none;
        `;
        
        // Assemble the editor
        this.wrapper.appendChild(this.toolbar);
        this.wrapper.appendChild(this.editorElement);
        
        // Add placeholder to editor
        this.editorElement.appendChild(this.placeholderElement);
        
        // Insert before textarea and hide textarea
        this.textarea.parentNode.insertBefore(this.wrapper, this.textarea);
        this.textarea.style.display = 'none';
        
        // Create toolbar buttons
        this.createToolbar();
    }
    
    createToolbar() {
        const buttons = [
            { command: 'bold', icon: 'B', title: 'Bold' },
            { command: 'italic', icon: 'I', title: 'Italic' },
            { command: 'underline', icon: 'U', title: 'Underline' },
            { separator: true },
            { command: 'bulletList', icon: '•', title: 'Bullet List' },
            { command: 'orderedList', icon: '1.', title: 'Numbered List' },
            { separator: true },
            { command: 'heading', level: 1, icon: 'H1', title: 'Heading 1' },
            { command: 'heading', level: 2, icon: 'H2', title: 'Heading 2' },
            { command: 'heading', level: 3, icon: 'H3', title: 'Heading 3' },
            { separator: true },
            { command: 'blockquote', icon: 'Quote', title: 'Quote' },
            { command: 'horizontalRule', icon: 'Line', title: 'Horizontal Line' },
            { separator: true },
            { command: 'insertTable', icon: '⊞', title: 'Insert Table' },
            { command: 'addRowBefore', icon: '↑', title: 'Add Row Above' },
            { command: 'addRowAfter', icon: '↓', title: 'Add Row Below' },
            { command: 'deleteRow', icon: '🗑️', title: 'Delete Row' },
            { command: 'addColumnBefore', icon: '←', title: 'Add Column Left' },
            { command: 'addColumnAfter', icon: '→', title: 'Add Column Right' },
            { command: 'deleteColumn', icon: '🗑️', title: 'Delete Column' },
            { command: 'deleteTable', icon: '✕', title: 'Delete Table' }
        ];
        
        buttons.forEach(button => {
            if (button.separator) {
                const separator = document.createElement('div');
                separator.style.cssText = 'width: 1px; background: #ddd; margin: 0 5px;';
                this.toolbar.appendChild(separator);
                return;
            }
            
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.innerHTML = button.icon;
            btn.title = button.title;
            btn.style.cssText = `
                padding: 5px 8px;
                border: 1px solid #ddd;
                background: white;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
                color: #333;
            `;
            
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.executeCommand(button.command, button.level);
            });
            
            btn.addEventListener('mouseenter', () => {
                btn.style.background = '#e9ecef';
            });
            
            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'white';
            });
            
            this.toolbar.appendChild(btn);
        });
    }
    
    initTiptap() {
        // For now, we'll use a simple contentEditable approach
        // In a real implementation, you would load Tiptap here
        this.editorElement.contentEditable = true;
        this.editorElement.setAttribute('data-placeholder', this.options.placeholder);
        
        // Add placeholder styling
        const style = document.createElement('style');
        style.textContent = `
            .tiptap-editor:empty:before {
                content: attr(data-placeholder);
                color: #999;
                pointer-events: none;
                position: absolute;
                top: 8px;
                left: 8px;
                font-style: italic;
                z-index: 1;
            }
            .tiptap-editor[data-empty="true"]:before {
                content: attr(data-placeholder);
                color: #999;
                pointer-events: none;
                position: absolute;
                top: 8px;
                left: 8px;
                font-style: italic;
                z-index: 1;
            }
            .tiptap-editor[data-empty="true"]:not(:focus):before {
                content: attr(data-placeholder);
                color: #999;
                pointer-events: none;
                position: absolute;
                top: 8px;
                left: 8px;
                font-style: italic;
                z-index: 1;
            }
            
            /* Pale Blue Clickable Areas */
            .pale-blue-area {
                margin: 10px 0;
                position: relative;
            }
            
            .clickable-surface {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 40px;
                background: #e7f3ff;
                border: 2px dashed #007bff;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                padding: 10px;
            }
            
            .clickable-surface:hover {
                background: #d1ecf1;
                border-color: #0056b3;
                transform: scale(1.02);
            }
            
            .area-hint {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #007bff;
                font-weight: bold;
                font-size: 14px;
                text-align: center;
            }
            
            .hint-icon {
                font-size: 16px;
            }
            
            .hint-text {
                font-size: 13px;
            }
            
            .content-area {
                display: none;
                min-height: 40px;
                padding: 10px;
                background: white;
                border: 1px solid #007bff;
                border-radius: 8px;
                outline: none;
                margin: 5px 0;
            }
            
            .content-area:focus {
                box-shadow: inset 0 0 0 2px rgba(0, 123, 255, 0.25);
            }
            
            .content-area p {
                margin: 0;
            }
            .tiptap-editor table {
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                border: 1px solid #ddd;
            }
            .tiptap-editor td, .tiptap-editor th {
                border: 1px solid #ddd !important;
                padding: 8px !important;
                text-align: left !important;
                vertical-align: top !important;
                min-height: 20px;
                box-sizing: border-box;
                position: relative;
            }
            /* Ensure table headers are properly aligned */
            .tiptap-editor th {
                text-align: left !important;
                vertical-align: top !important;
                background: #f2f2f2 !important;
                font-weight: bold !important;
                color: #333 !important;
            }
            .tiptap-editor td {
                background-color: white !important;
                font-weight: normal !important;
                color: #333 !important;
            }
            .tiptap-editor td:focus, .tiptap-editor th:focus {
                outline: 2px solid #007bff;
                outline-offset: -2px;
            }
            /* Ensure proper styling for dynamically created cells */
            .tiptap-editor table tr:first-child th {
                background-color: #f2f2f2 !important;
                font-weight: bold !important;
                text-align: left !important;
                vertical-align: top !important;
            }
            .tiptap-editor table tr:not(:first-child) td {
                background-color: white !important;
                font-weight: normal !important;
                text-align: left !important;
                vertical-align: top !important;
            }
            /* Force alignment for all table cells */
            .tiptap-editor table th,
            .tiptap-editor table td {
                text-align: left !important;
                vertical-align: top !important;
            }
            .tiptap-editor p {
                margin: 10px 0;
                min-height: 20px;
                padding: 5px 0;
            }
            /* Adjust bullet list indentation */
            .tiptap-editor ul {
                padding-left: 20px;
            }
            .tiptap-editor ol {
                padding-left: 20px;
            }
            .tiptap-editor li {
                margin-left: 0px;
            }
            .tiptap-editor p:empty {
                min-height: 30px;
                border: 1px dashed #e0e0e0;
                border-radius: 3px;
                margin: 15px 0;
            }
            .tiptap-editor p:empty:hover {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            .tiptap-editor p[data-spacing="true"]:empty {
                min-height: 25px;
                border: 1px dashed #c0c0c0;
                margin: 10px 0;
                pointer-events: auto;
                background-color: #fafafa;
                position: relative;
            }
            .tiptap-editor p[data-spacing="true"]:empty:hover {
                border-color: #007bff;
                background-color: #f0f8ff;
            }
            .tiptap-editor p[data-spacing="true"]:empty:after {
                content: "Click here to add text";
                position: absolute;
                top: 50%;
                left: 10px;
                transform: translateY(-50%);
                color: #999;
                font-size: 12px;
                pointer-events: none;
            }
            /* Make spacing paragraphs behave like input fields */
            .tiptap-editor p[data-spacing="true"] {
                position: relative;
                isolation: isolate;
                contain: layout style;
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                pointer-events: none;
                z-index: 1;
                min-height: 25px;
            }
            .tiptap-editor p[data-spacing="true"]:before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: transparent;
                z-index: 1;
                pointer-events: none;
            }
            /* Allow clicking on spacing paragraphs to add content */
            .tiptap-editor p[data-spacing="true"]:empty {
                pointer-events: auto;
            }
            /* Add a protective overlay for spacing paragraphs */
            .tiptap-editor p[data-spacing="true"]:before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: transparent;
                z-index: -1;
                pointer-events: none;
            }
        `;
        document.head.appendChild(style);
        
        // Load initial content
        if (this.textarea.value) {
            this.editorElement.innerHTML = this.textarea.value;
        }
        
        // Ensure empty paragraphs are present
        this.ensureEmptyParagraphs();
        
        // Check if editor is effectively empty and show placeholder
        this.updatePlaceholderVisibility();
        
        // Ensure all existing table cells have proper styling
        this.ensureTableCellStyling();
        
        // Set up periodic check to ensure spacing paragraphs are maintained
        setInterval(() => {
            this.ensureEmptyParagraphs();
        }, 2000); // Check every 2 seconds
        
        // Set up mutation observer to detect spacing paragraph removal
        this.setupMutationObserver();
        
        // Add global keydown protection for spacing paragraphs
        this.setupGlobalProtection();
        
        // Add cursor management for spacing paragraphs
        this.setupCursorManagement();
    }
    
    setupEventListeners() {
        // Sync content back to textarea on input
        this.editorElement.addEventListener('input', () => {
            this.updatePlaceholderVisibility();
            this.syncToTextarea();
        });
        
        // Handle paste events
        this.editorElement.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
        });
        
        // Ensure there are always empty paragraphs at start and end
        this.editorElement.addEventListener('click', (e) => {
            this.ensureEmptyParagraphs();
            this.positionCursorAtTopLeft(e);
        });
        
        // Also handle focus events to position cursor at top-left
        this.editorElement.addEventListener('focus', (e) => {
            this.positionCursorAtTopLeft(e);
        });
        
        // Update placeholder visibility on blur
        this.editorElement.addEventListener('blur', () => {
            this.updatePlaceholderVisibility();
        });
        
        // Also ensure empty paragraphs when content changes
        this.editorElement.addEventListener('input', () => {
            this.ensureEmptyParagraphs();
        });
        
        // Prevent deletion of spacing paragraphs - Enhanced protection
        this.editorElement.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' || e.key === 'Delete') {
                // Check if we're inside a table - if so, allow normal deletion
                const targetElement = e.target;
                if (targetElement.closest('table')) {
                    console.log('📍 Inside table - allowing normal deletion in local handler');
                    return;
                }
                
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const startContainer = range.startContainer;
                    const endContainer = range.endContainer;
                    
                    // Check both start and end containers
                    let startElement = startContainer;
                    let endElement = endContainer;
                    
                    while (startElement && startElement !== this.editorElement) {
                        if (startElement.nodeType === Node.ELEMENT_NODE && startElement.getAttribute('data-spacing') === 'true') {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('🚫 Prevented deletion of spacing paragraph (start)');
                            return;
                        }
                        startElement = startElement.parentNode;
                    }
                    
                    while (endElement && endElement !== this.editorElement) {
                        if (endElement.nodeType === Node.ELEMENT_NODE && endElement.getAttribute('data-spacing') === 'true') {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('🚫 Prevented deletion of spacing paragraph (end)');
                            return;
                        }
                        endElement = endElement.parentNode;
                    }
                    
                    // Only prevent deletion if it would cause cursor to jump into a table
                    const currentRange = selection.getRangeAt(0);
                    const currentStartContainer = currentRange.startContainer;
                    
                    // Check if we're about to delete a spacing paragraph that would cause cursor to jump to table
                    let element = currentStartContainer;
                    while (element && element !== this.editorElement) {
                        if (element.nodeType === Node.ELEMENT_NODE && element.getAttribute('data-spacing') === 'true') {
                            // Check if deleting this spacing paragraph would cause cursor to jump to adjacent table
                            const nextElement = element.nextElementSibling;
                            const prevElement = element.previousElementSibling;
                            
                            if ((nextElement && nextElement.tagName === 'TABLE') || 
                                (prevElement && prevElement.tagName === 'TABLE')) {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log('🚫 Prevented deletion of spacing paragraph that would cause table jump');
                                return;
                            }
                        }
                        element = element.parentNode;
                    }
                }
            }
        });
        
        // Also prevent deletion on input events - Enhanced protection
        this.editorElement.addEventListener('beforeinput', (e) => {
            if (e.inputType === 'deleteContentBackward' || e.inputType === 'deleteContentForward') {
                // Check if we're inside a table - if so, allow normal deletion
                const targetElement = e.target;
                if (targetElement.closest('table')) {
                    console.log('📍 Inside table - allowing normal input deletion in local handler');
                    return;
                }
                
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const startContainer = range.startContainer;
                    const endContainer = range.endContainer;
                    
                    // Check both start and end containers
                    let startElement = startContainer;
                    let endElement = endContainer;
                    
                    while (startElement && startElement !== this.editorElement) {
                        if (startElement.nodeType === Node.ELEMENT_NODE && startElement.getAttribute('data-spacing') === 'true') {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('🚫 Prevented input deletion of spacing paragraph (start)');
                            return;
                        }
                        startElement = startElement.parentNode;
                    }
                    
                    while (endElement && endElement !== this.editorElement) {
                        if (endElement.nodeType === Node.ELEMENT_NODE && endElement.getAttribute('data-spacing') === 'true') {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('🚫 Prevented input deletion of spacing paragraph (end)');
                            return;
                        }
                        endElement = endElement.parentNode;
                    }
                    
                    // Only prevent deletion if it would cause cursor to jump into a table
                    const inputRange = selection.getRangeAt(0);
                    const inputStartContainer = inputRange.startContainer;
                    
                    // Check if we're about to delete a spacing paragraph that would cause cursor to jump to table
                    let element = inputStartContainer;
                    while (element && element !== this.editorElement) {
                        if (element.nodeType === Node.ELEMENT_NODE && element.getAttribute('data-spacing') === 'true') {
                            // Check if deleting this spacing paragraph would cause cursor to jump to adjacent table
                            const nextElement = element.nextElementSibling;
                            const prevElement = element.previousElementSibling;
                            
                            if ((nextElement && nextElement.tagName === 'TABLE') || 
                                (prevElement && prevElement.tagName === 'TABLE')) {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log('🚫 Prevented input deletion of spacing paragraph that would cause table jump');
                                return;
                            }
                        }
                        element = element.parentNode;
                    }
                }
            }
        });
        
        // Additional protection for spacing paragraphs
        this.editorElement.addEventListener('input', (e) => {
            // Check if any spacing paragraphs were deleted
            const spacingParagraphs = this.editorElement.querySelectorAll('p[data-spacing="true"]');
            if (spacingParagraphs.length === 0) {
                // If all spacing paragraphs were deleted, recreate them
                this.ensureEmptyParagraphs();
                console.log('🔄 Recreated deleted spacing paragraphs');
            }
        });
        
        // Prevent selection of spacing paragraphs
        this.editorElement.addEventListener('selectstart', (e) => {
            let element = e.target;
            while (element && element !== this.editorElement) {
                if (element.nodeType === Node.ELEMENT_NODE && element.getAttribute('data-spacing') === 'true') {
                    e.preventDefault();
                    console.log('🚫 Prevented selection of spacing paragraph');
                    return;
                }
                element = element.parentNode;
            }
        });
        
        // Prevent multiple cell selection - Enhanced protection
        this.editorElement.addEventListener('mousedown', (e) => {
            const cell = e.target.closest('td, th');
            if (cell) {
                this.currentTableCell = cell;
                console.log('🖱️ Clicked inside table cell:', cell);
                
                // Clear any existing selection to prevent multi-cell selection
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const startCell = range.startContainer.closest ? range.startContainer.closest('td, th') : null;
                    const endCell = range.endContainer.closest ? range.endContainer.closest('td, th') : null;
                    
                    if (startCell && endCell && startCell !== endCell) {
                        e.preventDefault();
                        selection.removeAllRanges();
                        const newRange = document.createRange();
                        newRange.selectNodeContents(cell);
                        newRange.collapse(false);
                        selection.addRange(newRange);
                        console.log('🚫 Prevented multi-cell selection on mousedown');
                        return false;
                    }
                }
            }
        });
        
        this.editorElement.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                const endContainer = range.endContainer;
                
                // Check if selection spans multiple table cells
                const startCell = startContainer.closest ? startContainer.closest('td, th') : 
                    (startContainer.nodeType === Node.ELEMENT_NODE && (startContainer.tagName === 'TD' || startContainer.tagName === 'TH') ? startContainer : null);
                const endCell = endContainer.closest ? endContainer.closest('td, th') : 
                    (endContainer.nodeType === Node.ELEMENT_NODE && (endContainer.tagName === 'TD' || endContainer.tagName === 'TH') ? endContainer : null);
                
                if (startCell && endCell && startCell !== endCell) {
                    // Selection spans multiple cells - clear it and focus on start cell
                    e.preventDefault();
                    selection.removeAllRanges();
                    const newRange = document.createRange();
                    newRange.selectNodeContents(startCell);
                    newRange.collapse(false); // Collapse to end
                    selection.addRange(newRange);
                    this.currentTableCell = startCell;
                    console.log('🚫 Prevented multi-cell selection on mouseup');
                } else if (startCell) {
                    this.currentTableCell = startCell;
                }
            }
        });
        
        this.editorElement.addEventListener('selectionchange', () => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                const endContainer = range.endContainer;
                
                // Check if selection spans multiple table cells
                const startCell = startContainer.closest ? startContainer.closest('td, th') : 
                    (startContainer.nodeType === Node.ELEMENT_NODE && (startContainer.tagName === 'TD' || startContainer.tagName === 'TH') ? startContainer : null);
                const endCell = endContainer.closest ? endContainer.closest('td, th') : 
                    (endContainer.nodeType === Node.ELEMENT_NODE && (endContainer.tagName === 'TD' || endContainer.tagName === 'TH') ? endContainer : null);
                
                if (startCell && endCell && startCell !== endCell) {
                    // Selection spans multiple cells - clear it and focus on start cell
                    selection.removeAllRanges();
                    const newRange = document.createRange();
                    newRange.selectNodeContents(startCell);
                    newRange.collapse(false); // Collapse to end
                    selection.addRange(newRange);
                    this.currentTableCell = startCell;
                    console.log('🚫 Prevented multi-cell selection on selectionchange');
                } else if (startCell) {
                    this.currentTableCell = startCell;
                }
            }
        });
    }
    
    setupMutationObserver() {
        // Create a mutation observer to watch for spacing paragraph removal
        const observer = new MutationObserver((mutations) => {
            let spacingParagraphRemoved = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.removedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE && 
                            node.getAttribute && 
                            node.getAttribute('data-spacing') === 'true') {
                            spacingParagraphRemoved = true;
                            console.log('🚨 Mutation observer detected spacing paragraph removal!');
                        }
                    });
                }
            });
            
            // If a spacing paragraph was removed, recreate them immediately
            if (spacingParagraphRemoved) {
                setTimeout(() => {
                    this.ensureEmptyParagraphs();
                    console.log('🔄 Mutation observer recreated spacing paragraphs');
                }, 10);
            }
        });
        
        // Start observing
        observer.observe(this.editorElement, {
            childList: true,
            subtree: true
        });
        
        // Store observer reference for cleanup if needed
        this.mutationObserver = observer;
    }
    
    setupGlobalProtection() {
        // Add global document-level protection for spacing paragraphs only
        document.addEventListener('keydown', (e) => {
            // Only handle deletion keys
            if (e.key !== 'Backspace' && e.key !== 'Delete') {
                return;
            }
            
            // Check if the target is within our editor
            if (!this.editorElement.contains(e.target)) {
                return;
            }
            
            // Check if we're inside a table - if so, allow normal deletion
            const targetElement = e.target;
            if (targetElement.closest('table')) {
                console.log('📍 Inside table - allowing normal deletion');
                return;
            }
            
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                
                // Check if we're trying to delete a spacing paragraph
                let element = startContainer;
                while (element && element !== document.body) {
                    if (element.nodeType === Node.ELEMENT_NODE && 
                        element.getAttribute && 
                        element.getAttribute('data-spacing') === 'true') {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🚫 Global protection prevented spacing paragraph deletion');
                        return;
                    }
                    element = element.parentNode;
                }
                
                // Only prevent deletion if it would cause cursor to jump into a table
                let jumpElement = startContainer;
                while (jumpElement && jumpElement !== this.editorElement) {
                    if (jumpElement.nodeType === Node.ELEMENT_NODE && jumpElement.getAttribute('data-spacing') === 'true') {
                        // Check if deleting this spacing paragraph would cause cursor to jump to adjacent table
                        const nextElement = jumpElement.nextElementSibling;
                        const prevElement = jumpElement.previousElementSibling;
                        
                        if ((nextElement && nextElement.tagName === 'TABLE') || 
                            (prevElement && prevElement.tagName === 'TABLE')) {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('🚫 Global protection prevented deletion of spacing paragraph that would cause table jump');
                            return;
                        }
                    }
                    jumpElement = jumpElement.parentNode;
                }
            }
        }, true); // Use capture phase for maximum protection
        
        // Also add a global input event listener
        document.addEventListener('beforeinput', (e) => {
            // Only handle deletion input types
            if (e.inputType !== 'deleteContentBackward' && e.inputType !== 'deleteContentForward') {
                return;
            }
            
            // Check if the target is within our editor
            if (!this.editorElement.contains(e.target)) {
                return;
            }
            
            // Check if we're inside a table - if so, allow normal deletion
            const targetElement = e.target;
            if (targetElement.closest('table')) {
                console.log('📍 Inside table - allowing normal input deletion');
                return;
            }
            
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                
                // Check if we're trying to delete a spacing paragraph
                let element = startContainer;
                while (element && element !== document.body) {
                    if (element.nodeType === Node.ELEMENT_NODE && 
                        element.getAttribute && 
                        element.getAttribute('data-spacing') === 'true') {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🚫 Global beforeinput protection prevented spacing paragraph deletion');
                        return;
                    }
                    element = element.parentNode;
                }
            }
        }, true); // Use capture phase for maximum protection
    }
    
    setupCursorManagement() {
        // Monitor cursor movement and prevent jumping into tables
        this.editorElement.addEventListener('selectionchange', () => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                
                // Check if cursor jumped into a table from outside
                if (startContainer.closest && startContainer.closest('table')) {
                    // Check if the previous selection was in a spacing paragraph
                    if (this.lastSpacingSelection) {
                        const spacingParagraph = this.lastSpacingSelection;
                        
                        // If spacing paragraph still exists, return cursor to it
                        if (spacingParagraph.parentNode) {
                            const newRange = document.createRange();
                            newRange.setStart(spacingParagraph, 0);
                            newRange.collapse(true);
                            
                            selection.removeAllRanges();
                            selection.addRange(newRange);
                            
                            console.log('📍 Cursor returned to spacing paragraph - prevented jump to table');
                        }
                    }
                }
                
                // Track current selection in spacing paragraphs
                const spacingParagraph = startContainer.closest ? startContainer.closest('p[data-spacing="true"]') : null;
                if (spacingParagraph) {
                    this.lastSpacingSelection = spacingParagraph;
                } else {
                    this.lastSpacingSelection = null;
                }
            }
        });
        
        // Handle arrow keys to prevent jumping into tables from spacing paragraphs
        this.editorElement.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const startContainer = range.startContainer;
                    
                    // Check if cursor is in a spacing paragraph
                    const spacingParagraph = startContainer.closest ? startContainer.closest('p[data-spacing="true"]') : null;
                    
                    if (spacingParagraph) {
                        // Allow arrow key movement but monitor for table jumps
                        this.lastSpacingSelection = spacingParagraph;
                        
                        // Use a small delay to check if cursor jumped to table
                        setTimeout(() => {
                            const currentSelection = window.getSelection();
                            if (currentSelection.rangeCount > 0) {
                                const currentRange = currentSelection.getRangeAt(0);
                                const currentContainer = currentRange.startContainer;
                                
                                // If cursor jumped into table, bring it back
                                if (currentContainer.closest && currentContainer.closest('table') && spacingParagraph.parentNode) {
                                    const newRange = document.createRange();
                                    newRange.setStart(spacingParagraph, 0);
                                    newRange.collapse(true);
                                    
                                    currentSelection.removeAllRanges();
                                    currentSelection.addRange(newRange);
                                    
                                    console.log('📍 Arrow key prevented jump into table from spacing paragraph');
                                }
                            }
                        }, 10);
                    }
                }
            }
        });
        
        // Track spacing paragraph selection on click
        this.editorElement.addEventListener('click', (e) => {
            const target = e.target;
            const spacingParagraph = target.closest ? target.closest('p[data-spacing="true"]') : null;
            
            if (spacingParagraph) {
                this.lastSpacingSelection = spacingParagraph;
                console.log('📍 Clicked in spacing paragraph');
            } else {
                this.lastSpacingSelection = null;
            }
        });
    }
    
    executeCommand(command, value = null) {
        console.log(`Executing command: ${command}, value: ${value}`);
        
        switch (command) {
            case 'bold':
            case 'italic':
            case 'underline':
                document.execCommand(command, false, null);
                break;
                
            case 'bulletList':
                document.execCommand('insertUnorderedList', false, null);
                break;
                
            case 'orderedList':
                document.execCommand('insertOrderedList', false, null);
                break;
                
            case 'heading':
                const headingLevel = value || 1;
                document.execCommand('formatBlock', false, `h${headingLevel}`);
                break;
                
            case 'blockquote':
                document.execCommand('formatBlock', false, 'blockquote');
                break;
                
            case 'horizontalRule':
                document.execCommand('insertHorizontalRule', false, null);
                break;
                
            case 'insertTable':
                this.insertTable();
                break;
                
            case 'addRowBefore':
            case 'addRowAfter':
            case 'deleteRow':
            case 'addColumnBefore':
            case 'addColumnAfter':
            case 'deleteColumn':
            case 'deleteTable':
                this.handleTableCommand(command);
                break;
                
            default:
                console.log(`Unknown command: ${command}`);
        }
        
        this.syncToTextarea();
        this.editorElement.focus();
    }
    
    insertTable() {
        // Create table container with pale blue clickable areas
        const tableContainer = this.createTableContainer();
        
        // Insert table container at cursor position
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.insertNode(tableContainer);
            
            // Position cursor after table container
            range.setStartAfter(tableContainer);
            range.collapse(true);
            selection.removeAllRanges();
            selection.addRange(range);
        } else {
            this.editorElement.appendChild(tableContainer);
        }
        
        this.syncToTextarea();
    }
    
    createTableContainer() {
        const container = document.createElement('div');
        container.className = 'table-container';
        
        // Create pale blue clickable area before table
        const beforeArea = this.createPaleBlueClickableArea('before');
        container.appendChild(beforeArea);
        
        // Create the table
        const table = this.createTableElement();
        container.appendChild(table);
        
        // Create pale blue clickable area after table
        const afterArea = this.createPaleBlueClickableArea('after');
        container.appendChild(afterArea);
        
        return container;
    }
    
    createPaleBlueClickableArea(position) {
        const area = document.createElement('div');
        area.className = `pale-blue-area pale-blue-${position}`;
        
        const clickableSurface = document.createElement('div');
        clickableSurface.className = 'clickable-surface';
        clickableSurface.innerHTML = `
            <div class="area-hint">
                <span class="hint-icon">📝</span>
                <span class="hint-text">Click here to add text ${position === 'before' ? 'above' : 'below'} table</span>
            </div>
        `;
        
        const contentArea = document.createElement('div');
        contentArea.className = 'content-area';
        contentArea.contentEditable = true;
        contentArea.innerHTML = '<p><br></p>';
        
        area.appendChild(clickableSurface);
        area.appendChild(contentArea);
        
        // Add event listeners
        this.setupPaleBlueAreaEvents(area);
        
        return area;
    }
    
    setupPaleBlueAreaEvents(area) {
        const clickableSurface = area.querySelector('.clickable-surface');
        const contentArea = area.querySelector('.content-area');
        
        clickableSurface.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.activatePaleBlueArea(area);
        });
        
        contentArea.addEventListener('input', () => {
            this.syncToTextarea();
        });
        
        contentArea.addEventListener('blur', () => {
            this.handlePaleBlueAreaBlur(area);
        });
    }
    
    activatePaleBlueArea(area) {
        const clickableSurface = area.querySelector('.clickable-surface');
        const contentArea = area.querySelector('.content-area');
        
        clickableSurface.style.display = 'none';
        contentArea.style.display = 'block';
        contentArea.focus();
        
        // Position cursor at top-left
        const range = document.createRange();
        const selection = window.getSelection();
        range.setStart(contentArea, 0);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
        
        console.log('🎯 Pale blue area activated');
    }
    
    handlePaleBlueAreaBlur(area) {
        const clickableSurface = area.querySelector('.clickable-surface');
        const contentArea = area.querySelector('.content-area');
        
        const hasContent = contentArea.textContent.trim().length > 0;
        
        if (!hasContent) {
            contentArea.style.display = 'none';
            clickableSurface.style.display = 'flex';
        }
    }
    
    createTableElement() {
        // Create the actual table
        const table = document.createElement('table');
        table.style.cssText = `
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        `;
        
        // Create table with proper th/td elements
        const headerRow = document.createElement('tr');
        for (let i = 1; i <= 3; i++) {
            const th = document.createElement('th');
            th.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: #f2f2f2; font-weight: bold; color: #333; text-align: left !important; vertical-align: top !important;';
            th.contentEditable = true;
            th.innerHTML = `Header ${i}`;
            th.setAttribute('data-cell-type', 'header');
            headerRow.appendChild(th);
        }
        table.appendChild(headerRow);
        
        // Create data rows
        for (let row = 1; row <= 2; row++) {
            const tr = document.createElement('tr');
            for (let col = 1; col <= 3; col++) {
                const td = document.createElement('td');
                td.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: white; color: #333; text-align: left; vertical-align: top;';
                td.contentEditable = true;
                td.innerHTML = `Cell ${(row - 1) * 3 + col}`;
                td.setAttribute('data-cell-type', 'data');
                tr.appendChild(td);
            }
            table.appendChild(tr);
        }
        
        // Insert table with spacing paragraphs
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            
            // Insert before paragraph, table, and after paragraph
            range.insertNode(afterParagraph);
            range.insertNode(table);
            range.insertNode(beforeParagraph);
            
            // Position cursor in the after paragraph
            range.setStart(afterParagraph, 0);
            range.setEnd(afterParagraph, 0);
            selection.removeAllRanges();
            selection.addRange(range);
        } else {
            // Append to editor if no selection
            this.editorElement.appendChild(beforeParagraph);
            this.editorElement.appendChild(table);
            this.editorElement.appendChild(afterParagraph);
            
            // Position cursor in the after paragraph
            const range = document.createRange();
            range.setStart(afterParagraph, 0);
            range.setEnd(afterParagraph, 0);
            selection.removeAllRanges();
            selection.addRange(range);
        }
        
        console.log('✅ Table inserted with automatic spacing');
    }
    
    ensureEmptyParagraphs() {
        // Ensure there's an empty paragraph at the beginning
        const firstChild = this.editorElement.firstChild;
        if (!firstChild || firstChild.nodeName !== 'P') {
            const emptyP = document.createElement('p');
            emptyP.innerHTML = '<br>';
            emptyP.setAttribute('data-spacing', 'true');
            emptyP.setAttribute('data-isolated', 'true'); // Mark as isolated
            this.editorElement.insertBefore(emptyP, firstChild);
        }
        
        // Ensure there's an empty paragraph at the end
        const lastChild = this.editorElement.lastChild;
        if (!lastChild || lastChild.nodeName !== 'P') {
            const emptyP = document.createElement('p');
            emptyP.innerHTML = '<br>';
            emptyP.setAttribute('data-spacing', 'true');
            emptyP.setAttribute('data-isolated', 'true'); // Mark as isolated
            this.editorElement.appendChild(emptyP);
        }
        
        // Ensure empty paragraphs around tables
        const children = Array.from(this.editorElement.children);
        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            if (child.nodeName === 'TABLE') {
                // Check if there's a paragraph before the table
                if (i === 0 || children[i - 1].nodeName !== 'P') {
                    const emptyP = document.createElement('p');
                    emptyP.innerHTML = '<br>';
                    emptyP.setAttribute('data-spacing', 'true');
                    emptyP.setAttribute('data-isolated', 'true'); // Mark as isolated
                    this.editorElement.insertBefore(emptyP, child);
                    children.splice(i, 0, emptyP);
                    i++; // Skip the paragraph we just added
                }
                
                // Check if there's a paragraph after the table
                if (i === children.length - 1 || children[i + 1].nodeName !== 'P') {
                    const emptyP = document.createElement('p');
                    emptyP.innerHTML = '<br>';
                    emptyP.setAttribute('data-spacing', 'true');
                    emptyP.setAttribute('data-isolated', 'true'); // Mark as isolated
                    this.editorElement.insertBefore(emptyP, children[i + 1] || null);
                }
            }
        }
    }
    
    ensureTableCellStyling() {
        const tables = this.editorElement.querySelectorAll('table');
        tables.forEach((table, tableIndex) => {
            console.log(`🔧 Ensuring styling for table ${tableIndex} with ${table.rows.length} rows`);
            
            for (let i = 0; i < table.rows.length; i++) {
                const row = table.rows[i];
                const isHeaderRow = i === 0;
                
                for (let j = 0; j < row.cells.length; j++) {
                    const cell = row.cells[j];
                    
                    // Ensure proper element type
                    if (isHeaderRow && cell.nodeName !== 'TH') {
                        console.log(`Converting td to th in header row ${i}, cell ${j}`);
                        const newCell = document.createElement('th');
                        newCell.innerHTML = cell.innerHTML;
                        newCell.contentEditable = true;
                        newCell.setAttribute('data-cell-type', 'header');
                        cell.parentNode.replaceChild(newCell, cell);
                        continue;
                    } else if (!isHeaderRow && cell.nodeName !== 'TD') {
                        console.log(`Converting th to td in data row ${i}, cell ${j}`);
                        const newCell = document.createElement('td');
                        newCell.innerHTML = cell.innerHTML;
                        newCell.contentEditable = true;
                        newCell.setAttribute('data-cell-type', 'data');
                        cell.parentNode.replaceChild(newCell, cell);
                        continue;
                    }
                    
                    // Apply proper styling
                    if (isHeaderRow) {
                        cell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: #f2f2f2; font-weight: bold; color: #333; text-align: left !important; vertical-align: top !important;';
                        cell.setAttribute('data-cell-type', 'header');
                    } else {
                        cell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: white; color: #333; text-align: left !important; vertical-align: top !important;';
                        cell.setAttribute('data-cell-type', 'data');
                    }
                    
                    // Ensure contentEditable and editability
                    if (!cell.contentEditable || cell.contentEditable !== 'true') {
                        cell.contentEditable = true;
                    }
                    
                    // Ensure cell has content (add <br> if empty)
                    if (!cell.innerHTML.trim() || cell.innerHTML.trim() === '') {
                        cell.innerHTML = '<br>';
                    }
                }
            }
        });
        
        console.log('✅ Table cell styling ensured');
    }
    
    handleTableCommand(command) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) {
            console.log('No selection for table command');
            return;
        }
        
        // Find the table cell
        let cell = selection.anchorNode;
        while (cell && cell.nodeName !== 'TD' && cell.nodeName !== 'TH' && cell !== document.body) {
            cell = cell.parentNode;
        }
        
        if (!cell || (cell.nodeName !== 'TD' && cell.nodeName !== 'TH')) {
            console.log('Not in a table cell');
            return;
        }
        
        const table = cell.closest('table');
        if (!table) {
            console.log('No table found');
            return;
        }
        
        const row = cell.parentNode;
        const rowIndex = Array.from(table.rows).indexOf(row);
        const cellIndex = Array.from(row.cells).indexOf(cell);
        
        console.log(`Table command: ${command}, Row: ${rowIndex}, Cell: ${cellIndex}`);
        
        switch (command) {
            case 'addRowBefore':
                this.insertRow(table, rowIndex);
                break;
            case 'addRowAfter':
                this.insertRow(table, rowIndex + 1);
                break;
            case 'deleteRow':
                if (table.rows.length > 1) {
                    row.remove();
                } else {
                    alert('Cannot delete the last row. Delete the entire table instead.');
                }
                break;
            case 'addColumnBefore':
                this.insertColumn(table, cellIndex);
                break;
            case 'addColumnAfter':
                this.insertColumn(table, cellIndex + 1);
                break;
            case 'deleteColumn':
                if (row.cells.length > 1) {
                    this.deleteColumn(table, cellIndex);
                } else {
                    alert('Cannot delete the last column. Delete the entire table instead.');
                }
                break;
            case 'deleteTable':
                table.remove();
                break;
        }
        
        console.log(`✅ Table command ${command} executed`);
    }
    
    insertRow(table, index) {
        const newRow = table.insertRow(index);
        const firstRow = table.rows[0];
        
        for (let i = 0; i < firstRow.cells.length; i++) {
            // Check if we're inserting at position 0 (header row) or after
            const isHeaderRow = index === 0;
            
            let newCell;
                if (isHeaderRow) {
                    // Create header cell element
                    newCell = document.createElement('th');
                    newCell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: #f2f2f2; font-weight: bold; color: #333; text-align: left !important; vertical-align: top !important;';
                } else {
                    // Create regular cell element
                    newCell = document.createElement('td');
                    newCell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: white; color: #333; text-align: left !important; vertical-align: top !important;';
                }
            
            newCell.contentEditable = true;
            newCell.innerHTML = '<br>'; // Add a line break to make it editable
            newCell.setAttribute('data-cell-type', isHeaderRow ? 'header' : 'data');
            newRow.appendChild(newCell);
        }
        
        console.log(`✅ Row inserted at position ${index} with proper ${index === 0 ? 'header' : 'data'} cell elements`);
    }
    
    insertColumn(table, index) {
        console.log(`🔧 Inserting column at index ${index} in table with ${table.rows.length} rows`);
        
        for (let i = 0; i < table.rows.length; i++) {
            const row = table.rows[i];
            console.log(`Processing row ${i}, has ${row.cells.length} cells`);
            
            // Check if this is a header row (first row) to determine cell type
            const isHeaderRow = i === 0;
            
            let newCell;
                if (isHeaderRow) {
                    // Create header cell element
                    newCell = document.createElement('th');
                    newCell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: #f2f2f2; font-weight: bold; color: #333; text-align: left !important; vertical-align: top !important;';
                    console.log(`Creating header cell (th) for row ${i}`);
                } else {
                    // Create regular cell element
                    newCell = document.createElement('td');
                    newCell.style.cssText = 'border: 1px solid #ddd; padding: 8px; background: white; color: #333; text-align: left !important; vertical-align: top !important;';
                    console.log(`Creating data cell (td) for row ${i}`);
                }
            
            newCell.contentEditable = true;
            newCell.innerHTML = '<br>'; // Add a line break to make it editable
            newCell.setAttribute('data-cell-type', isHeaderRow ? 'header' : 'data');
            
            // Insert the cell at the specified index
            if (index >= row.cells.length) {
                row.appendChild(newCell);
                console.log(`Appended cell to end of row ${i}`);
            } else {
                row.insertBefore(newCell, row.cells[index]);
                console.log(`Inserted cell at position ${index} in row ${i}`);
            }
        }
        
        console.log('✅ Column inserted with proper header/data cell elements');
    }
    
    deleteColumn(table, index) {
        for (let i = 0; i < table.rows.length; i++) {
            if (table.rows[i].cells[index]) {
                table.rows[i].deleteCell(index);
            }
        }
    }
    
    updatePlaceholderVisibility() {
        // Check if editor is effectively empty (only has empty paragraphs with <br> tags)
        const hasContent = this.editorElement.textContent.trim().length > 0;
        
        console.log('🔍 Placeholder check - hasContent:', hasContent, 'textContent:', this.editorElement.textContent);
        
        if (hasContent) {
            this.editorElement.removeAttribute('data-empty');
            if (this.placeholderElement) {
                this.placeholderElement.style.display = 'none';
            }
            console.log('🚫 Placeholder hidden - content exists');
        } else {
            this.editorElement.setAttribute('data-empty', 'true');
            if (this.placeholderElement) {
                this.placeholderElement.style.display = 'block';
            }
            console.log('✅ Placeholder shown - editor is empty');
        }
    }
    
    positionCursorAtTopLeft(e) {
        // Small delay to ensure the event is processed
        setTimeout(() => {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const startContainer = range.startContainer;
                
                // Check if we're in a spacing paragraph or empty content
                const spacingParagraph = startContainer.closest ? startContainer.closest('p[data-spacing="true"]') : null;
                
                if (spacingParagraph || !this.editorElement.textContent.trim()) {
                    // Position cursor at the very beginning of the editor
                    const newRange = document.createRange();
                    newRange.setStart(this.editorElement, 0);
                    newRange.collapse(true);
                    
                    selection.removeAllRanges();
                    selection.addRange(newRange);
                    
                    console.log('🎯 Cursor positioned at top-left of editor');
                }
            }
        }, 10);
    }
    
    syncToTextarea() {
        this.textarea.value = this.editorElement.innerHTML;
        
        // Update placeholder visibility
        this.updatePlaceholderVisibility();
        
        // Trigger change event for auto-save
        const event = new Event('input', { bubbles: true });
        this.textarea.dispatchEvent(event);
    }
    
    getContent() {
        return this.editorElement.innerHTML;
    }
    
    setContent(content) {
        this.editorElement.innerHTML = content;
        this.syncToTextarea();
    }
}

// Auto-initialize on textareas with notes-textarea class
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea.notes-textarea');
    textareas.forEach(textarea => {
        if (!textarea.previousElementSibling?.classList.contains('tiptap-wrapper')) {
            new TiptapEditor(textarea.id, {
                placeholder: textarea.placeholder || 'Enter notes for this subject...'
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

console.log('✅ TiptapEditor loaded');
