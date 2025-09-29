#!/bin/bash

echo "🧪 Rich Text Editor Test Suite"
echo "==============================="
echo ""

# Check if HTTP server is running
echo "🔍 Checking if test server is running..."
if curl -s "http://localhost:8002/test_comprehensive.html" > /dev/null; then
    echo "✅ Test server is running on port 8002"
else
    echo "❌ Test server is not running. Please start it with:"
    echo "   cd /home/steli/dev/school_organizer && python3 -m http.server 8002"
    echo ""
    echo "🚀 Starting test server..."
    cd /home/steli/dev/school_organizer && python3 -m http.server 8002 &
    SERVER_PID=$!
    sleep 2
    echo "✅ Test server started (PID: $SERVER_PID)"
fi

echo ""
echo "📄 Test pages available:"
echo "   • http://localhost:8002/test_comprehensive.html - Comprehensive automated tests"
echo "   • http://localhost:8002/test_editor_functionality.html - Manual testing interface"
echo "   • http://localhost:8002/test_editor_automated.html - Automated test suite"
echo ""

echo "🧪 Key Features to Test:"
echo "========================"
echo ""
echo "1. 🛡️ Multi-Cell Selection Prevention:"
echo "   - Insert a table"
echo "   - Try to select text across multiple cells"
echo "   - Selection should be limited to single cells"
echo ""
echo "2. 🔒 Spacing Paragraph Protection:"
echo "   - Insert a table (creates spacing paragraphs)"
echo "   - Try to delete the spacing paragraph after the table"
echo "   - Deletion should be prevented"
echo ""
echo "3. 📋 Bullet List Indentation:"
echo "   - Create bullet lists in editor"
echo "   - Bullets should not be too far to the right"
echo "   - Test both in regular text and table cells"
echo ""
echo "4. 📐 Table Cell Alignment:"
echo "   - Insert a table"
echo "   - Add text to cells"
echo "   - Text should be top-left aligned"
echo ""
echo "5. 🔧 Table Operations:"
echo "   - Add/remove rows and columns"
echo "   - New cells should have proper styling"
echo "   - All cells should be editable"
echo ""

echo "🎯 Automated Test Instructions:"
echo "==============================="
echo ""
echo "1. Open: http://localhost:8002/test_comprehensive.html"
echo "2. Click 'Setup Editor' to initialize"
echo "3. Click 'Insert Table' to add a table"
echo "4. Click 'Run All Tests' to run automated tests"
echo "5. Review the test results and summary"
echo ""

echo "🔍 Manual Test Instructions:"
echo "============================"
echo ""
echo "1. Open: http://localhost:8002/test_editor_functionality.html"
echo "2. Follow the step-by-step instructions for each test"
echo "3. Check console for debug messages"
echo "4. Verify all functionality works as expected"
echo ""

echo "📊 Expected Results:"
echo "===================="
echo ""
echo "✅ Multi-cell selection should be prevented"
echo "✅ Spacing paragraphs should be protected from deletion"
echo "✅ Bullet lists should have reasonable indentation"
echo "✅ Table cells should have top-left text alignment"
echo "✅ Table operations should work correctly"
echo "✅ All cells should be editable"
echo ""

echo "🚀 Ready to test! Open the test pages in your browser."
echo ""

# Keep the script running to maintain the server
if [ ! -z "$SERVER_PID" ]; then
    echo "Press Ctrl+C to stop the test server..."
    wait $SERVER_PID
fi
