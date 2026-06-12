import os
import shutil

def main():
    print("Starting Roadshub initialization...")
    
    # 1. Ensure required Flask folders exist
    os.makedirs('app/static/css', exist_ok=True)
    os.makedirs('app/templates', exist_ok=True)
    print("Verified directories app/static/css and app/templates")

    # 2. Copy styles.css to static/css/styles.css
    if os.path.exists('styles.css'):
        shutil.copy('styles.css', 'app/static/css/styles.css')
        print("Successfully copied styles.css to app/static/css/styles.css")
    else:
        print("Warning: styles.css not found in root")

    # 3. Read index.html and perform Jinja2 replacements, saving it to app/templates/index.html
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Replace stylesheet reference
        content = content.replace('href="styles.css"', 'href="{{ url_for(\'static\', filename=\'css/styles.css\') }}"')
        
        # Replace main navbar and footer links
        content = content.replace('href="index.html"', 'href="{{ url_for(\'main.index\') }}"')
        content = content.replace('href="https://roadshub.org/dashboard/"', 'href="{{ url_for(\'main.login\') }}"')
        
        # Link other pages to the login / dashboard or placeholder for clean routing
        content = content.replace('href="courses.html"', 'href="{{ url_for(\'main.login\') }}"')
        content = content.replace('href="about.html"', 'href="#"')
        content = content.replace('href="contact.html"', 'href="#"')
        
        with open('app/templates/index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully compiled and saved app/templates/index.html")
    else:
        print("Warning: index.html not found in root")

if __name__ == '__main__':
    main()
