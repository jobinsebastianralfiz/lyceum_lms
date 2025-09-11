// Django Admin Rich Text Editor for Course fields
document.addEventListener('DOMContentLoaded', function() {
    // Find all textareas with the rich-text-editor class
    const richTextFields = document.querySelectorAll('textarea.rich-text-editor');
    
    richTextFields.forEach(function(textarea) {
        // Skip if already processed
        if (textarea.style.display === 'none') return;
        
        // Create editor container
        const editorContainer = document.createElement('div');
        editorContainer.style.height = '200px';
        editorContainer.style.border = '1px solid #ccc';
        editorContainer.style.borderRadius = '4px';
        editorContainer.style.marginBottom = '10px';
        
        // Insert editor container before textarea
        textarea.parentNode.insertBefore(editorContainer, textarea);
        
        // Hide the original textarea
        textarea.style.display = 'none';
        
        // Configure Quill toolbar
        const toolbarOptions = [
            [{ 'header': [1, 2, 3, false] }],
            ['bold', 'italic', 'underline'],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'indent': '-1'}, { 'indent': '+1' }],
            [{ 'color': [] }, { 'background': [] }],
            ['clean']
        ];
        
        // Initialize Quill editor
        const editor = new Quill(editorContainer, {
            modules: {
                toolbar: toolbarOptions
            },
            theme: 'snow',
            placeholder: textarea.placeholder || 'Enter content here...'
        });
        
        // Load existing content from textarea
        if (textarea.value) {
            editor.root.innerHTML = textarea.value;
        }
        
        // Sync editor content to textarea on change
        editor.on('text-change', function() {
            textarea.value = editor.root.innerHTML;
        });
        
        // Sync content before form submission
        const form = textarea.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                textarea.value = editor.root.innerHTML;
            });
        }
    });
});