from flask import Flask, request, jsonify, render_template
import math

app = Flask(__name__)

# Core calculations mapping
OPERATIONS = {
    'add': lambda x, y: x + y,
    'subtract': lambda x, y: x - y,
    'multiply': lambda x, y: x * y,
    'divide': lambda x, y: x / y,
    'power': lambda x, y: math.pow(x, y),
    'mod': lambda x, y: x % y
}

OP_SYMBOLS = {
    'add': '+',
    'subtract': '-',
    'multiply': '×',
    'divide': '÷',
    'power': '^',
    'mod': '%'
}

@app.route('/')
def index():
    """Renders the single-page calculator frontend."""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """
    API endpoint to handle calculator operations.
    Expects a JSON payload with:
        - num1: float/int
        - num2: float/int
        - operation: str ('add', 'subtract', 'multiply', 'divide', 'power', 'mod')
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Extract values
        num1_str = data.get('num1')
        num2_str = data.get('num2')
        operation = data.get('operation')

        # Basic validations
        if num1_str is None or num2_str is None or not operation:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Type conversion
        try:
            num1 = float(num1_str)
            num2 = float(num2_str)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid numerical inputs'}), 400

        # Operation check
        if operation not in OPERATIONS:
            return jsonify({'success': False, 'error': f"Unsupported operation '{operation}'"}), 400

        # Division by zero check
        if operation in ['divide', 'mod'] and num2 == 0:
            return jsonify({'success': False, 'error': 'Cannot divide by zero'}), 400

        # Perform computation
        result = OPERATIONS[operation](num1, num2)

        # Handle formatting to avoid floating point anomalies like 0.1 + 0.2 = 0.30000000000000004
        if result.is_integer():
            result = int(result)
        else:
            # Round to 10 decimal places to look neat but preserve detail
            result = round(result, 10)

        # Pretty display string
        symbol = OP_SYMBOLS.get(operation, '?')
        expression = f"{num1_str} {symbol} {num2_str}"

        return jsonify({
            'success': True,
            'result': result,
            'operation': operation,
            'expression': expression,
            'server_processed': True
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    print("Starting Flask Calculator Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
