"""
Flask application for the chatbot UI in Phase 3 implementation.
Provides a simple web interface for interacting with the agent system.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import requests
from datetime import datetime
from mcp_server import MCPFallbackHandler
from agents.chatbot_agent import AgentOrchestrator


def create_app():
    """Create and configure the Flask application."""
    import os
    template_dir = os.path.abspath('templates')
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-for-hackathon')

    # Initialize the agent orchestrator and fallback handler
    orchestrator = AgentOrchestrator()
    fallback_handler = MCPFallbackHandler()

    # Get backend API URL
    BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:8000')

    def get_auth_token():
        """Get authentication token from session if available."""
        return session.get('token')

    def make_api_request(method, endpoint, json_data=None, headers=None):
        """Make an API request to the backend with authentication."""
        token = get_auth_token()

        request_headers = {
            'Content-Type': 'application/json'
        }

        if token:
            request_headers['Authorization'] = f'Bearer {token}'

        if headers:
            request_headers.update(headers)

        url = f"{BACKEND_API_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                headers=request_headers,
                timeout=30
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            # Return a mock response structure
            class MockResponse:
                def __init__(self, status_code, json_data):
                    self.status_code = status_code
                    self._json_data = json_data

                def json(self):
                    return self._json_data

            return MockResponse(500, {"detail": f"Connection error: {str(e)}"})

    @app.route('/')
    def index():
        """Render the main chatbot interface."""
        is_logged_in = get_auth_token() is not None
        return render_template('index.html', is_logged_in=is_logged_in)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login."""
        if request.method == 'POST':
            try:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')

                if not email or not password:
                    return jsonify({'success': False, 'error': 'Email and password required'}), 400

                # Call backend login API
                response = make_api_request('POST', '/api/auth/login', {
                    'email': email,
                    'password': password
                })

                if response.status_code in [200, 201]:
                    try:
                        token_data = response.json()
                        session['token'] = token_data['access_token']
                        session['user_email'] = email
                        return jsonify({'success': True, 'message': 'Login successful'})
                    except:
                        return jsonify({'success': False, 'error': 'Invalid response from server'}), 500
                else:
                    try:
                        error_data = response.json()
                        return jsonify({'success': False, 'error': error_data.get('detail', 'Login failed')}), response.status_code
                    except:
                        return jsonify({'success': False, 'error': f'Login failed with status {response.status_code}'}), response.status_code

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        return render_template('login.html')

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        """Handle user registration."""
        if request.method == 'POST':
            try:
                data = request.get_json()
                email = data.get('email')
                password = data.get('password')

                if not email or not password:
                    return jsonify({'success': False, 'error': 'Email and password required'}), 400

                # Call backend signup API
                response = make_api_request('POST', '/api/auth/signup', {
                    'email': email,
                    'password': password
                })

                if response.status_code in [200, 201]:
                    try:
                        token_data = response.json()
                        session['token'] = token_data['access_token']
                        session['user_email'] = email
                        return jsonify({'success': True, 'message': 'Account created successfully'})
                    except:
                        return jsonify({'success': False, 'error': 'Invalid response from server'}), 500
                else:
                    try:
                        error_data = response.json()
                        return jsonify({'success': False, 'error': error_data.get('detail', 'Signup failed')}), response.status_code
                    except:
                        return jsonify({'success': False, 'error': f'Signup failed with status {response.status_code}'}), response.status_code

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        return render_template('signup.html')

    @app.route('/logout', methods=['POST'])
    def logout():
        """Handle user logout."""
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})

    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Handle chat messages from the frontend."""
        try:
            data = request.get_json()
            user_message = data.get('message', '').strip()

            if not user_message:
                return jsonify({
                    'success': False,
                    'message': 'Empty message received',
                    'timestamp': datetime.now().isoformat()
                }), 400

            # Check if this is a task operation that should go to the backend
            user_message_lower = user_message.lower()

            # Determine if this is a task operation (expanded list)
            is_task_operation = any(op in user_message_lower for op in [
                'add task', 'create task', 'list task', 'show task', 'update task',
                'complete task', 'delete task', 'remove task', 'task summary',
                'add a task', 'create a task', 'list my tasks', 'show my tasks',
                'update task', 'complete task', 'delete task', 'remove task',
                'mark task', 'finish task', 'done task', 'task list', 'tasks list',
                'list all', 'list tasks', 'show all tasks', 'show tasks'
            ])

            # If authenticated and it's a task operation, try to use the backend API
            if is_task_operation and get_auth_token():
                print(f"Detected task operation: {user_message}, attempting backend API call...")

                # For task operations, use the backend API directly
                response = make_api_request('POST', '/api/chat/', {
                    'message': user_message
                })

                if response.status_code in [200, 201]:
                    try:
                        backend_data = response.json()
                        print(f"Backend API response: {backend_data}")

                        # Map backend response to expected frontend format
                        success = backend_data.get('status') == 'success'
                        message = backend_data.get('message', '')

                        response_data = {
                            'success': success,
                            'user_message': user_message,
                            'message': message,
                            'agent_response': {'message': message} if success else {},
                            'error': None if success else 'Backend API returned error status',
                            'fallback_used': False,
                            'timestamp': datetime.now().isoformat()
                        }

                        return jsonify(response_data)
                    except Exception as e:
                        print(f"Error parsing backend response: {str(e)}")
                        # Continue to fallback if there's an issue parsing the response
                else:
                    # If backend API fails, fall back to local orchestrator
                    print(f"Backend API call failed with status {response.status_code}, falling back to local orchestrator")
                    print(f"Response content: {getattr(response, '_json_data', 'Could not read')}")
            elif is_task_operation and not get_auth_token():
                print(f"Task operation detected but user not authenticated: {user_message}")

            # If not a task operation or backend is unavailable, use local orchestrator
            def native_execute():
                return orchestrator.process_user_input(user_message)

            result = fallback_handler.execute_with_fallback(
                user_message,
                native_execute
            )

            # Prepare response
            response_data = {
                'success': result.get('success', False),
                'user_message': user_message,
                'agent_response': result.get('response', {}) if result.get('success', False) else {},
                'error': result.get('error', None),
                'fallback_used': result.get('fallback_used', False),
                'timestamp': datetime.now().isoformat(),
                'message': result.get('response', {}).get('message', '') if result.get('success', False) else 'An error occurred processing your request'
            }

            return jsonify(response_data)

        except Exception as e:
            return jsonify({
                'success': False,
                'user_message': user_message if 'user_message' in locals() else '',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'message': f'An unexpected error occurred: {str(e)}'
            }), 500

    @app.route('/api/tasks', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def tasks():
        """Proxy task operations to the backend."""
        if request.method == 'OPTIONS':
            # Handle preflight requests
            response = jsonify({})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,PATCH')
            return response

        if not get_auth_token():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        method = request.method
        json_data = request.get_json() if request.is_json else None

        # Get task ID from URL parameters if present
        import urllib.parse
        from flask import request as flask_request
        full_path = flask_request.full_path
        task_id = None
        if '/api/tasks/' in full_path:
            # Extract task ID from URL
            parts = full_path.split('/api/tasks/')
            if len(parts) > 1 and parts[1]:
                task_id = parts[1].split('/')[0].split('?')[0]

        # Build the backend endpoint
        if task_id:
            endpoint = f'/api/tasks/{task_id}'
            if 'toggle' in full_path and method == 'PATCH':
                endpoint += '/toggle'
        else:
            endpoint = '/api/tasks'

        response = make_api_request(method, endpoint, json_data)

        # Handle the response properly
        if response.status_code in [200, 201]:
            try:
                return jsonify(response.json()), response.status_code
            except:
                return jsonify({'success': True}), response.status_code
        elif response.status_code == 204:  # No content for DELETE
            return jsonify({'success': True}), 204
        else:
            try:
                error_data = response.json()
                return jsonify({'success': False, 'error': error_data}), response.status_code
            except:
                return jsonify({'success': False, 'error': f'Backend API error: {response.status_code}'}), response.status_code

    @app.route('/api/auth/check')
    def auth_check():
        """Check if user is authenticated."""
        token = get_auth_token()
        is_logged_in = token is not None
        return jsonify({
            'logged_in': is_logged_in,
            'user_email': session.get('user_email') if is_logged_in else None
        })

    @app.route('/api/status')
    def status():
        """Check the status of the agent system."""
        try:
            # Test if the orchestrator is working
            test_result = orchestrator.process_user_input("status check")

            return jsonify({
                'status': 'operational',
                'agent_system': 'available',
                'timestamp': datetime.now().isoformat(),
                'test_result': test_result
            })
        except Exception as e:
            return jsonify({
                'status': 'degraded',
                'agent_system': 'unavailable',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/favicon.ico')
    def favicon():
        """Serve an empty response for favicon to avoid 404 errors."""
        from flask import Response
        # Return empty response with 204 No Content to prevent 404 errors
        return Response(status=204)

    return app


# Create the app instance
app = create_app()


if __name__ == '__main__':
    # Only for development/testing
    app.run(debug=True, host='0.0.0.0', port=5000)