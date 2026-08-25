# Funmiyo SkillQuest 🎮📚

An interactive, adaptive mathematics learning platform for elementary students (K-Grade 5) featuring engaging games, progress tracking, and personalized learning paths.

## 📋 Features

- **Grade-Specific Learning**: Customized math problems for KG through Grade 5
- **Multiple Game Modes**:
  - 🚀 **Math Blaster** - Timed arcade-style challenges
  - 🎯 **Math Sprint** - Quick-fire problem sets
  - 💣 **Bubble Shooter** - Bubble-popping math puzzles
  - ⚔️ **Boss Battle** - Epic math duels
  
- **Role-Based Access**:
  - **Students**: Interactive games with personalized dashboards
  - **Teachers**: Monitor student progress and assign content
  - **Parents**: Track child's learning metrics
  - **Admins**: System management and school configuration

- **Adaptive Learning Engine**: Adjusts difficulty based on performance
- **Real-Time Analytics**: Track progress, scores, and learning patterns
- **Multi-School Support**: Support for different schools with custom configurations

## 🛠️ Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Analytics**: Custom analytics engine

## 📦 Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/aakanksha06/Funmiyo-Gamified-learning.git
   cd Funmiyo-SkillQuest
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python app.py
   ```
   The database will be created automatically on first run.

5. **Run the application**
   ```bash
   python app.py
   ```
   Visit: `http://localhost:5000`

## 🎓 Grade Configuration

The platform supports customized difficulty levels for each grade:

| Grade | Operations | Max Number | Time Limit | Focus |
|-------|-----------|-----------|-----------|-------|
| KG | + | 5 | 120s | Counting & basics |
| Grade 1 | + | 10 | 100s | Addition to 10 |
| Grade 2 | +, - | 20 | 90s | Addition & subtraction |
| Grade 3 | +, - | 50 | 80s | Larger numbers |
| Grade 4 | +, -, × | 99 | 70s | Times tables |
| Grade 5 | +, -, ×, ÷ | 100 | 60s | All operations |

## 👥 User Roles

- **Admin**: Full system control, school management
- **Teacher**: Create assignments, monitor student performance
- **Parent**: View child's progress and analytics
- **Student**: Play games, earn scores, build skills

## 📊 Project Structure

```
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── analytics/
│   ├── __init__.py
│   └── engine.py            # Analytics engine
├── database/
│   └── schema.sql           # Database schema
├── static/
│   ├── css/
│   │   └── global.css       # Styling
│   └── js/
│       └── adaptive_engine.js # Game logic
└── templates/
    ├── login.html           # Authentication
    ├── hub.html             # Main hub
    ├── admin/               # Admin dashboards
    ├── games/               # Game interfaces
    ├── student/             # Student dashboards
    ├── teacher/             # Teacher dashboards
    └── parent/              # Parent dashboards
```

## 🚀 Deployment

### Heroku
```bash
heroku login
heroku create your-app-name
git push heroku main
heroku open
```

### Render.com
1. Connect GitHub repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Deploy

### PythonAnywhere
1. Upload code to PythonAnywhere
2. Configure web app with Flask settings
3. Reload app

## 📝 Default Login Credentials

After first run, create admin account through the registration interface or check database initialization logs.

## 🔐 Security Notes

- Change the `SECRET_KEY` in production
- Use environment variables for sensitive data
- Enable HTTPS on deployed instances
- Regularly update dependencies

## 🐛 Troubleshooting

**Database errors?**
- Delete `database/skillquest.db` and restart to reinitialize

**Port already in use?**
- Change port: `python app.py --port 5001`

**Import errors?**
- Ensure all dependencies are installed: `pip install -r requirements.txt`

## 📖 Usage

1. **Register** as a student, teacher, or parent
2. **Select grade level** (KG-Grade 5)
3. **Choose a game** and start learning!
4. **Track progress** through personalized dashboards
5. **Compete** in timed challenges

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

**Happy Learning! 🎓✨**

*Funmiyo SkillQuest - Making Math Fun & Interactive*
