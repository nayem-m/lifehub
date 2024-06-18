'''
LifeHub, an app to organize your life
Life areas managing app inspired by the PARA method
Based on a relational database that links all areas of life

By Moosa Nayem    
'''

from flask import Flask, request, render_template, redirect, url_for, flash
from sqlalchemy import DateTime, String, Text, Integer, Column, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


webServer = Flask(__name__)
webServer.secret_key = 'verysecret'
webServer.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(webServer)


class Area(db.Model):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.now)
    title = Column(String(100), nullable=False)
    tasks = relationship("Task", back_populates="area")
    projects = relationship("Project", back_populates="area")
    archive = Column(Boolean, default=False)

    def __repr__(self):
        return f"{self.id} {self.title} {self.created}"

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(Integer, primary_key=True)
    created = db.Column(DateTime, default=datetime.now)
    title = db.Column(String(100), nullable=False)
    area_id = db.Column(Integer, ForeignKey('areas.id'))
    area = relationship("Area", back_populates="projects")
    tasks = relationship("Task", back_populates="project")
    due_date = db.Column(String(30))
    archive = db.Column(Boolean)

    def __repr__(self):
        return f"{self.id} {self.title} {self.area} {self.due_date} "

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(Integer, primary_key=True)
    title = db.Column(String(100), nullable=False)
    created = db.Column(DateTime, default=datetime.now)
    area_id = db.Column(Integer, ForeignKey('areas.id'))
    area = relationship("Area", back_populates="tasks")
    content = db.Column(Text)
    due_date = db.Column(String)
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship("Project", back_populates="tasks")
    archive = db.Column(Boolean, default=False)
    sources = relationship("Sources", back_populates="task")

    def __repr__(self):
        return f"Task (id={self.id}, title={self.title}, created={self.created}"

class Sources(db.Model):
    __tabelname__ = "resources"
    id = db.Column(Integer, primary_key=True)
    title = db.Column(String(100), nullable=False)
    source_type = db.Column(String)
    task_id = db.Column(Integer, ForeignKey('tasks.id'))
    task = relationship("Task", back_populates="sources")

    def __repr__(self):
        return f"Source {self.id}"

#Function to help with limiting areas duplicates
def check_area_repeats(area):
    all_areas = Area.query.all()
    n = 0
    while n < len(all_areas):
        if all_areas[n].title == area.title:
            return True
        n += 1
    return False

with webServer.app_context():
    db.create_all()

@webServer.route('/')
def index():
    return render_template('main.html')

# Adding tasks page
@webServer.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if request.method == 'POST':
        task_title = request.form['title']
        task_area = request.form['area']
        task_project = request.form['project']
        task_duedate = request.form.get('due')
        task_content = request.form['content']
        task_archive = request.form.get('archive') == 'on'
        resource_title = request.form['resource_title']
        resource_type = request.form['resource_type']
        selected_area = Area.query.get(task_area)
        selected_project = Project.query.get(task_project)

        if not task_title:
            flash('Title is required', 'danger')
        elif not task_content:
            flash('No content has been added', 'warning')
        else:
            new_task = Task(title=task_title, area=selected_area, project=selected_project, due_date=task_duedate, content=task_content, archive=task_archive)
            db.session.add(new_task)
            db.session.commit()
            if not resource_title and not resource_type:
                flash('Task created without a source', 'warning')
            else:
                new_resource = Sources(title=resource_title, source_type=resource_type, task=new_task)
                db.session.add(new_resource)
                db.session.commit()
                flash('Task created with source', 'success')
        return redirect(url_for('tasks'))

    filtered_tasks = Task.query.order_by(Task.created.desc()).filter_by(archive=False).all()
    all_areas = Area.query.all()
    all_projects = Project.query.all()
    return render_template('tasks.html', tasks=filtered_tasks, areas=all_areas, projects=all_projects)


# Adding areas page
@webServer.route('/areas', methods=['GET', 'POST'])
def areas():
    if request.method == 'POST':
        title = request.form['title']
        archive = request.form.get('archive') == 'on'
        new_area = Area(title=title, archive=archive)

        # Go through all areas and check them
        while check_area_repeats(new_area):
            flash('Duplicate title', 'danger')
            return redirect(url_for('areas'))

        if check_area_repeats(new_area):
            flash('Area already exists.', 'danger')
            db.session.rollback()
        else:
            db.session.add(new_area)
            db.session.commit()
            flash('Area created.', 'success')

        return redirect(url_for('areas'))

    ordered_areas = Area.query.order_by(Area.created.desc()).filter_by(archive=False).all()
    all_projects = Project.query.all()
    all_tasks = Task.query.all()

    return render_template('areas.html', tasks=all_tasks, areas=ordered_areas, projects=all_projects)

# Adding projects page
@webServer.route('/projects', methods=['GET', 'POST'])
def projects():
    if request.method == 'POST':
        title = request.form['title']
        area = request.form['area']
        archive = request.form.get('archive') == 'on'
        selected_area = Area.query.get(area)
        duedate = request.form.get('due')

        if not title or not duedate:
            flash('Title or due date parameters missing.', 'danger')
        elif not selected_area:
            flash('Area missing.', 'error')
        else:
            new_project = Project(title=title, area=selected_area, due_date=duedate, archive=archive)
            db.session.add(new_project)
            db.session.commit()
            flash('Project created.', 'success')

        return redirect(url_for('projects'))

    ordered_projects = Project.query.order_by(Project.created.desc()).filter_by(archive=False).all()
    all_areas = Area.query.all()
    all_tasks = Task.query.all()
    return render_template('projects.html', projects=ordered_projects, areas=all_areas, tasks=all_tasks)

# Archive page
@webServer.route('/archive')
def archive():
    archived_tasks = []
    archived_areas = []
    archived_projects = []

    tasks = Task.query.all()
    areas = Area.query.all()
    projects = Project.query.all()

    for task in tasks:
        if task.archive == True:
            archived_tasks.append(task)

    for area in areas:
        if area.archive == True:
            archived_areas.append(area)

    for project in projects:
        if project.archive == True:
            archived_projects.append(project)

    return render_template('archive.html', archived_areas=archived_areas, archived_projects=archived_projects, archived_tasks=archived_tasks)

# Functions below here edit the different objects
@webServer.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task_title = request.form['title']
        task_project = request.form['project']
        task_duedate = request.form.get('due')
        task_content = request.form['content']
        task_archive = request.form.get('archive') == 'on'
        task_area = request.form['area']
        selected_area = Area.query.get(task_area)
        selected_project = Project.query.get(task_project)

        if task_archive == True:
            task.archive = task_archive
            flash('Task archived.', 'warning')
        else:
            task.title = task_title
            task.content = task_content
            task.due_date = task_duedate
            task.project = selected_project
            task.area = selected_area
            flash('Task edited.', 'success')

        db.session.commit()
        return redirect(url_for('tasks'))

    all_areas = Area.query.all()
    all_projects = Project.query.all()
    return render_template('edit_task.html', task=task, areas=all_areas, projects=all_projects)

@webServer.route('/areas/edit/<int:area_id>', methods=['GET', 'POST'])
def edit_area(area_id):
    area = Area.query.get_or_404(area_id)

    if request.method == 'POST':
        title = request.form['title']
        archive = request.form.get('archive') == 'on'

        if archive == True:
            area.archive = archive
            flash('Area archived', 'warning')
        else:
            area.title = title
            flash('Area edited.', 'success')

        db.session.commit()
        return redirect(url_for('areas'))

    return render_template('edit_area.html', area=area)

@webServer.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        title = request.form['title']
        area = request.form['area']
        selected_area = Area.query.get(area)
        archive = request.form.get('archive') == 'on'

        if archive == True:
            project.archive = archive
            flash('Project archived', 'warning')
        else:
            project.title = title
            project.area = selected_area
            flash('Project edited.', 'success')

        db.session.commit()
        return redirect(url_for('projects'))

    all_areas = Area.query.all()
    return render_template('edit_project.html', project=project, areas=all_areas)

# Functions below allows to delete objects
@webServer.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'danger')
    return redirect(url_for('tasks'))

@webServer.route('/delete_area/<int:area_id>', methods=['POST'])
def delete_area(area_id):
    area = Area.query.get_or_404(area_id)
    db.session.delete(area)
    db.session.commit()
    flash('Area deleted.', 'danger')
    return redirect(url_for('areas'))

@webServer.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted.', 'danger')
    return redirect(url_for('projects'))

# Unarchive button functionality in the archive page
@webServer.route('/unarchive_area/<int:area_id>', methods=['POST'])
def unarchive_area(area_id):
    area = Area.query.get_or_404(area_id)
    area.archive = False
    db.session.commit()
    flash('Area unarchived.', 'warning')
    return redirect(url_for('archive'))

@webServer.route('/unarchive_project/<int:project_id>', methods=['POST'])
def unarchive_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.archive = False
    db.session.commit()
    flash('Project unarchived.', 'warning')
    return redirect(url_for('archive'))

@webServer.route('/unarchive_task/<int:task_id>', methods=['POST'])
def unarchive_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.archive = False
    db.session.commit()
    flash('Task unarchived.', 'warning')
    return redirect(url_for('archive'))


if __name__ == "__main__":
    webServer.run(debug=True)
