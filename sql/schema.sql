CREATE TABLE dbo.departments (
    department_id INT IDENTITY(1,1) NOT NULL,
    department_code VARCHAR(10) NOT NULL,
    department_name NVARCHAR(100) NOT NULL,
    location NVARCHAR(100) NOT NULL,
    CONSTRAINT PK_departments PRIMARY KEY (department_id),
    CONSTRAINT UQ_departments_department_code UNIQUE (department_code),
    CONSTRAINT UQ_departments_department_name UNIQUE (department_name)
);
GO

CREATE TABLE dbo.employees (
    employee_id INT IDENTITY(1,1) NOT NULL,
    employee_number VARCHAR(20) NOT NULL,
    department_id INT NOT NULL,
    manager_id INT NULL,
    first_name NVARCHAR(60) NOT NULL,
    last_name NVARCHAR(60) NOT NULL,
    email VARCHAR(254) NOT NULL,
    job_title NVARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL,
    employment_status VARCHAR(20) NOT NULL
        CONSTRAINT DF_employees_employment_status DEFAULT ('Active'),
    CONSTRAINT PK_employees PRIMARY KEY (employee_id),
    CONSTRAINT UQ_employees_employee_number UNIQUE (employee_number),
    CONSTRAINT UQ_employees_email UNIQUE (email),
    CONSTRAINT FK_employees_department
        FOREIGN KEY (department_id) REFERENCES dbo.departments (department_id),
    CONSTRAINT FK_employees_manager
        FOREIGN KEY (manager_id) REFERENCES dbo.employees (employee_id),
    CONSTRAINT CK_employees_employment_status
        CHECK (employment_status IN ('Active', 'OnLeave', 'Terminated')),
    CONSTRAINT CK_employees_not_own_manager
        CHECK (manager_id IS NULL OR manager_id <> employee_id)
);
GO

CREATE TABLE dbo.projects (
    project_id INT IDENTITY(1,1) NOT NULL,
    project_code VARCHAR(20) NOT NULL,
    department_id INT NOT NULL,
    project_name NVARCHAR(150) NOT NULL,
    project_description NVARCHAR(500) NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    project_status VARCHAR(20) NOT NULL
        CONSTRAINT DF_projects_project_status DEFAULT ('Planned'),
    CONSTRAINT PK_projects PRIMARY KEY (project_id),
    CONSTRAINT UQ_projects_project_code UNIQUE (project_code),
    CONSTRAINT FK_projects_department
        FOREIGN KEY (department_id) REFERENCES dbo.departments (department_id),
    CONSTRAINT CK_projects_date_range
        CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT CK_projects_project_status
        CHECK (project_status IN ('Planned', 'Active', 'Completed', 'OnHold', 'Cancelled'))
);
GO

CREATE TABLE dbo.employee_projects (
    employee_id INT NOT NULL,
    project_id INT NOT NULL,
    project_role NVARCHAR(100) NOT NULL,
    allocation_percent DECIMAL(5,2) NOT NULL,
    assigned_on DATE NOT NULL,
    released_on DATE NULL,
    CONSTRAINT PK_employee_projects PRIMARY KEY (employee_id, project_id),
    CONSTRAINT FK_employee_projects_employee
        FOREIGN KEY (employee_id) REFERENCES dbo.employees (employee_id),
    CONSTRAINT FK_employee_projects_project
        FOREIGN KEY (project_id) REFERENCES dbo.projects (project_id),
    CONSTRAINT CK_employee_projects_allocation
        CHECK (allocation_percent > 0 AND allocation_percent <= 100),
    CONSTRAINT CK_employee_projects_date_range
        CHECK (released_on IS NULL OR released_on >= assigned_on)
);
GO

CREATE INDEX IX_employees_department_id ON dbo.employees (department_id);
CREATE INDEX IX_employees_manager_id ON dbo.employees (manager_id);
CREATE INDEX IX_projects_department_id ON dbo.projects (department_id);
CREATE INDEX IX_employee_projects_project_id ON dbo.employee_projects (project_id);
GO
