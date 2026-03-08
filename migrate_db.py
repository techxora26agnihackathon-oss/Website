from app import create_app
from models import db

app = create_app()
with app.app_context():
    # Update schema
    db.create_all()
    
    # Check if we need to add problem_id column to teams (if not already handled by create_all)
    # create_all won't add columns to existing tables in SQLite/SQLAlchemy easily without migrations
    from sqlalchemy import text
    try:
        db.session.execute(text('ALTER TABLE teams ADD COLUMN problem_id INTEGER REFERENCES problem_statements(id)'))
        db.session.commit()
        print("Column problem_id added to teams table.")
    except Exception as e:
        db.session.rollback()
        print(f"Update info: {e}")

    # Add domain column to problem_statements
    try:
        db.session.execute(text('ALTER TABLE problem_statements ADD COLUMN domain VARCHAR(100)'))
        db.session.commit()
        print("Column domain added to problem_statements table.")
    except Exception as e:
        db.session.rollback()
        print(f"ProblemStatement update info: {e}")

    # We need to import ProblemStatement to use it
    from models import ProblemStatement

    # Clear old ones if we want a fresh start
    try:
        db.session.query(ProblemStatement).delete()
        db.session.commit()
        print("Cleared old problem statements.")
    except Exception as e:
        db.session.rollback()
        print(f"Clear info: {e}")

    domain_mapping = {
        'CS': 'Climate & Sustainability Tech',
        'HT': 'HealthTech',
        'ET': 'EdTech',
        'CY': 'Cybersecurity',
        'SI': 'Student Innovation'
    }

    new_problems = [
        # Climate & Sustainability Tech
        ("CS", "Smart Campus Energy Optimization System", "Educational institutions consume a significant amount of electricity across classrooms, laboratories, hostels, libraries, and administrative buildings. However, the lack of real-time monitoring and analytical insights often leads to energy wastage, higher operational costs, and increased carbon footprint. In this challenge, participants are required to design and develop a Smart Campus Energy Optimization System that monitors real-time electricity usage across different campus buildings and provides data-driven recommendations to reduce energy consumption. The proposed solution should include mechanisms to collect or simulate energy usage data, analyze consumption patterns, detect inefficiencies, and generate actionable suggestions such as reducing peak-hour usage, identifying abnormal consumption, or recommending energy-efficient practices. A user-friendly dashboard for administrators should display building-wise energy metrics, usage trends, comparisons, and optimization insights. Teams are expected to deliver a working prototype demonstrating real-time monitoring (or simulated real-time data), analytics capabilities, and practical energy-saving recommendations. The solution should focus on scalability, sustainability impact, usability, and feasibility for real world campus implementation."),
        ("CS", "AI-Based Smart Waste Segregation & Tracking", "Improper waste segregation is a major environmental challenge in educational institutions and public spaces. When dry, wet, and recyclable waste are mixed together, it becomes difficult to process, recycle, or dispose of them efficiently, leading to increased landfill waste and environmental pollution. In this challenge, participants are required to design and develop an AI-Based Smart Waste Segregation & Tracking System that uses image recognition technology to automatically identify and classify waste into categories such as dry, wet, and plastic. The proposed solution should include an image processing or computer vision model capable of detecting the type of waste through a camera interface or uploaded images. Additionally, the system must provide a dashboard that tracks and visualizes waste generation trends over time, such as daily or weekly waste distribution, most common waste types, and recycling efficiency insights. Teams are expected to deliver a working prototype demonstrating waste classification and an analytics dashboard with meaningful visualizations. The solution should focus on accuracy, usability, scalability, and its potential to improve sustainability practices in real-world campus or community environments."),
        
        # HealthTech
        ("HT", "AI-Powered Mental Health Support for Students", "College students often experience high levels of stress due to academic pressure, personal challenges, career uncertainty, and social factors. However, access to immediate mental health support is often limited due to stigma, lack of awareness, or insufficient resources. In this challenge, participants are required to design and develop an AI-Powered Mental Health Support Platform that assists students in identifying and managing stress through a chatbot or digital interface. The system should analyze user inputs (text responses, mood entries, or interaction patterns) to assess stress levels and provide appropriate guidance. The proposed solution must include features such as stress detection based on conversational input, personalized coping strategies (breathing exercises, mindfulness techniques, productivity tips), mood tracking over time, and access to verified emergency support resources. The platform should ensure privacy, data security, and responsible AI usage. Teams are expected to deliver a functional prototype demonstrating conversational interaction, basic stress analysis, and supportive recommendations. The solution should prioritize user safety, ethical design, usability, and real-world applicability within a campus environment."),
        ("HT", "Rural Telemedicine Assistance Platform", "Access to quality healthcare remains a significant challenge in rural and remote areas due to limited medical infrastructure, shortage of doctors, and connectivity constraints. Many patients are required to travel long distances for basic consultations, resulting in delayed treatment and increased healthcare costs. In this challenge, participants are required to design and develop a Rural Telemedicine Assistance Platform that enables rural patients to connect with qualified doctors through a lightweight and accessible digital solution. The platform should be optimized for low-bandwidth environments and support essential features such as appointment scheduling, virtual consultations (video/audio/text-based), and basic diagnostic data sharing. The proposed solution must also include secure storage and management of digital health records, ensuring patient data privacy and compliance with ethical data handling practices. Features such as multilingual support, offline data syncing, and simple user interfaces for non technical users are encouraged. Teams are expected to deliver a working prototype that demonstrates patient-doctor interaction, secure data handling, and adaptability to rural conditions. The solution should focus on accessibility, scalability, reliability, and real-world healthcare impact."),

        # EdTech
        ("ET", "Personalized AI Learning Assistant", "Students have diverse learning styles, strengths, weaknesses, and learning speeds. Traditional one-size-fits-all teaching methods often fail to address individual learning gaps, resulting in reduced engagement and academic performance. There is a growing need for intelligent systems that can adapt to each student’s unique learning pattern. In this challenge, participants are required to design and develop a Personalized AI Learning Assistant that analyzes a student’s performance, strengths, weaknesses, and pace of learning to generate customized study plans and learning paths. The proposed solution should include features such as performance assessment (quizzes or input based evaluation), adaptive content recommendations, progress tracking, and dynamic adjustment of difficulty levels. The system may provide topic-wise insights, revision suggestions, practice exercises, and milestone tracking to enhance learning efficiency. Teams are expected to deliver a functional prototype demonstrating personalization logic, AI driven recommendations, and an intuitive user interface. The solution should focus on adaptability, accuracy, user engagement, scalability, and its potential to improve student learning outcomes in real-world educational environments."),
        ("ET", "Skill-to-Job Matching Platform", "Many students struggle to identify suitable career paths due to a lack of clarity about industry expectations and the skills required for specific job roles. This gap between academic learning and industry demand often results in underemployment, skill mismatch, and missed career opportunities. In this challenge, participants are required to design and develop a Skill-to-Job Matching Platform that analyzes a student’s skills, interests, certifications, and academic background to recommend relevant internships, job roles, certifications, and career paths aligned with current industry demand. The proposed solution should include a skill assessment or profile-building feature, an intelligent matching algorithm, and a recommendation system that suggests targeted learning resources, industry-recognized certifications, and potential career trajectories. The platform may also provide insights into in-demand skills, skill gap analysis, and personalized improvement plans. Teams are expected to deliver a functional prototype demonstrating skill analysis, recommendation logic, and a user-friendly interface. The solution should focus on relevance, accuracy, scalability, and its potential to bridge the gap between education and employment in real-world scenarios."),

        # Cybersecurity
        ("CY", "Phishing Detection & Awareness Tool", "Phishing attacks are one of the most common and dangerous forms of cyber threats, targeting users through fake emails, malicious links, and fraudulent websites. Many individuals fall victim due to a lack of awareness and the inability to identify suspicious content in real time. These attacks can result in data theft, financial loss, and compromised digital identities. In this challenge, participants are required to design and develop a Phishing Detection & Awareness Tool in the form of a browser extension or application that detects potentially malicious links and warns users before they access harmful content. The proposed solution should include features such as URL analysis, detection of suspicious patterns, domain verification checks, and real-time alert mechanisms. Additionally, the system must educate users by explaining why a link is considered unsafe and provide guidance on safe browsing practices. Incorporating machine learning models, blacklist databases, or heuristic analysis methods is encouraged. Teams are expected to deliver a working prototype demonstrating phishing detection capabilities and an interactive user interface that promotes cybersecurity awareness. The solution should focus on accuracy, real-time performance, usability, scalability, and user data privacy."),
        ("CY", "Secure Digital Identity Verification System", "With the rapid growth of digital services, secure and reliable identity verification has become essential. Traditional password-based authentication systems are vulnerable to breaches, identity theft, and unauthorized access. There is a growing need for privacy-focused authentication mechanisms that enhance security while protecting user data. In this challenge, participants are required to design and develop a Secure Digital Identity Verification System that implements multi-factor authentication (MFA), biometric verification, or a combination of advanced authentication techniques to ensure strong identity validation. The proposed solution should include secure login mechanisms such as OTP-based verification, facial recognition, fingerprint authentication (simulated if necessary), or device-based authentication. The system must prioritize user privacy by implementing data encryption, secure storage practices, minimal data collection, and protection against common cyber threats. Teams are expected to deliver a working prototype demonstrating secure authentication flow, identity verification logic, and data protection mechanisms. The solution should focus on security strength, privacy compliance, usability, scalability, and real-world applicability in digital platforms."),

        # Student Innovation
        ("SI", "Student Innovation / Open Problem", "In the Student Innovation domain, participants are encouraged to identify a real-world problem faced by students, educational institutions, or society and develop an innovative, practical, and scalable solution within 24 hours. The solution can be in the form of a web or mobile application, AI-based system, IoT prototype, automation tool, platform, or any technical product that demonstrates creativity and impact. Teams must clearly define the problem they are solving, justify its relevance, and propose a feasible solution that can be implemented in real-world scenarios. The project should focus on improving areas such as student productivity, campus management, accessibility, sustainability, mental well-being, skill development, or community support. Participants are expected to deliver a working prototype along with a clear explanation of the technology used, potential users, scalability, and future enhancements. Innovation, originality, usability, and practical impact will be key evaluation criteria.")
    ]

    for shortcode, title, desc in new_problems:
        ps = ProblemStatement(
            problem_title=title,
            description=desc,
            domain=shortcode,
            max_teams=7
        )
        db.session.add(ps)
    
    db.session.commit()
    print("New problem statements seeded.")

print("Database update complete.")
