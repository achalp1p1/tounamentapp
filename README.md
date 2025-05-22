# Tournament Management System

A web-based tournament management system built with Flask for managing table tennis tournaments, player registrations, and tournament draws.

## Features

- Player Registration and Management
- Tournament Creation and Management
- Tournament Registration
- Seeding Management
- Draw Generation
- File Upload Support
- State Registration Integration

## Setup Instructions

1. Clone the repository:
```bash
git clone [your-repository-url]
cd tournamentapp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

- `app.py` - Main application file
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)
- `config/` - Configuration files
- `uploads/` - Uploaded files directory

## Dependencies

- Flask
- Python 3.x
- Other dependencies listed in requirements.txt

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
