PRAGMA foreign_keys = ON;

CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_code TEXT NOT NULL UNIQUE,
    department_name TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    employee_number TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL,
    manager_id INTEGER,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    job_title TEXT NOT NULL,
    hire_date TEXT NOT NULL CHECK (date(hire_date) IS NOT NULL),
    employment_status TEXT NOT NULL DEFAULT 'Active'
        CHECK (employment_status IN ('Active', 'OnLeave', 'Terminated')),
    CONSTRAINT fk_employees_department
        FOREIGN KEY (department_id) REFERENCES departments (department_id),
    CONSTRAINT fk_employees_manager
        FOREIGN KEY (manager_id) REFERENCES employees (employee_id),
    CONSTRAINT ck_employees_not_own_manager
        CHECK (manager_id IS NULL OR manager_id <> employee_id)
);

CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY,
    project_code TEXT NOT NULL UNIQUE,
    department_id INTEGER NOT NULL,
    project_name TEXT NOT NULL,
    project_description TEXT,
    start_date TEXT NOT NULL CHECK (date(start_date) IS NOT NULL),
    end_date TEXT CHECK (end_date IS NULL OR date(end_date) IS NOT NULL),
    project_status TEXT NOT NULL DEFAULT 'Planned'
        CHECK (project_status IN ('Planned', 'Active', 'Completed', 'OnHold', 'Cancelled')),
    CONSTRAINT fk_projects_department
        FOREIGN KEY (department_id) REFERENCES departments (department_id),
    CONSTRAINT ck_projects_date_range
        CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE employee_projects (
    employee_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    project_role TEXT NOT NULL,
    allocation_percent NUMERIC NOT NULL
        CHECK (allocation_percent > 0 AND allocation_percent <= 100),
    assigned_on TEXT NOT NULL CHECK (date(assigned_on) IS NOT NULL),
    released_on TEXT CHECK (released_on IS NULL OR date(released_on) IS NOT NULL),
    CONSTRAINT pk_employee_projects PRIMARY KEY (employee_id, project_id),
    CONSTRAINT fk_employee_projects_employee
        FOREIGN KEY (employee_id) REFERENCES employees (employee_id),
    CONSTRAINT fk_employee_projects_project
        FOREIGN KEY (project_id) REFERENCES projects (project_id),
    CONSTRAINT ck_employee_projects_date_range
        CHECK (released_on IS NULL OR released_on >= assigned_on)
);

CREATE INDEX ix_employees_department_id ON employees (department_id);
CREATE INDEX ix_employees_manager_id ON employees (manager_id);
CREATE INDEX ix_projects_department_id ON projects (department_id);
CREATE INDEX ix_employee_projects_project_id ON employee_projects (project_id);
