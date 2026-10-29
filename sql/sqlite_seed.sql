BEGIN TRANSACTION;

INSERT INTO departments (department_id, department_code, department_name, location)
VALUES
    (1, 'ENG', 'Engineering', 'Seattle'),
    (2, 'HR', 'Human Resources', 'Chicago'),
    (3, 'FIN', 'Finance', 'New York'),
    (4, 'MKT', 'Marketing', 'Austin'),
    (5, 'OPS', 'Operations', 'Denver');

INSERT INTO employees
    (employee_id, employee_number, department_id, manager_id, first_name, last_name, email, job_title, hire_date, employment_status)
VALUES
    (1, 'E0001', 1, NULL, 'Ava', 'Patel', 'ava.patel@example.com', 'Engineering Director', '2018-03-12', 'Active'),
    (2, 'E0002', 2, NULL, 'Liam', 'Chen', 'liam.chen@example.com', 'HR Director', '2019-06-03', 'Active'),
    (3, 'E0003', 3, NULL, 'Noah', 'Garcia', 'noah.garcia@example.com', 'Finance Director', '2017-11-20', 'Active'),
    (4, 'E0004', 4, NULL, 'Mia', 'Johnson', 'mia.johnson@example.com', 'Marketing Director', '2020-01-13', 'Active'),
    (5, 'E0005', 5, NULL, 'Ethan', 'Williams', 'ethan.williams@example.com', 'Operations Director', '2016-09-26', 'Active'),
    (6, 'E0006', 1, 1, 'Sophia', 'Kim', 'sophia.kim@example.com', 'Senior Software Engineer', '2020-02-10', 'Active'),
    (7, 'E0007', 1, 1, 'Oliver', 'Brown', 'oliver.brown@example.com', 'Data Engineer', '2021-05-17', 'Active'),
    (8, 'E0008', 1, 6, 'Isabella', 'Davis', 'isabella.davis@example.com', 'Software Engineer', '2022-08-01', 'Active'),
    (9, 'E0009', 1, 6, 'Lucas', 'Martinez', 'lucas.martinez@example.com', 'QA Engineer', '2023-04-24', 'Active'),
    (10, 'E0010', 2, 2, 'Amelia', 'Wilson', 'amelia.wilson@example.com', 'HR Business Partner', '2020-07-06', 'Active'),
    (11, 'E0011', 2, 2, 'James', 'Taylor', 'james.taylor@example.com', 'Recruiter', '2022-02-14', 'Active'),
    (12, 'E0012', 2, 10, 'Harper', 'Anderson', 'harper.anderson@example.com', 'People Operations Specialist', '2024-01-08', 'Active'),
    (13, 'E0013', 3, 3, 'Benjamin', 'Thomas', 'benjamin.thomas@example.com', 'Finance Manager', '2019-10-07', 'Active'),
    (14, 'E0014', 3, 13, 'Evelyn', 'Jackson', 'evelyn.jackson@example.com', 'Financial Analyst', '2021-03-15', 'Active'),
    (15, 'E0015', 3, 13, 'Henry', 'White', 'henry.white@example.com', 'Accountant', '2022-11-28', 'Active'),
    (16, 'E0016', 4, 4, 'Abigail', 'Harris', 'abigail.harris@example.com', 'Marketing Manager', '2020-05-04', 'Active'),
    (17, 'E0017', 4, 16, 'Alexander', 'Martin', 'alexander.martin@example.com', 'Content Strategist', '2021-09-13', 'Active'),
    (18, 'E0018', 4, 16, 'Ella', 'Thompson', 'ella.thompson@example.com', 'Campaign Analyst', '2023-06-19', 'Active'),
    (19, 'E0019', 5, 5, 'Daniel', 'Moore', 'daniel.moore@example.com', 'Operations Manager', '2019-04-22', 'Active'),
    (20, 'E0020', 5, 19, 'Scarlett', 'Lee', 'scarlett.lee@example.com', 'Business Process Analyst', '2022-07-11', 'Active');

INSERT INTO projects
    (project_id, project_code, department_id, project_name, project_description, start_date, end_date, project_status)
VALUES
    (1, 'PRJ-1001', 1, 'Customer Portal Modernization', 'Rebuild the customer-facing portal on the current application platform.', '2025-01-06', NULL, 'Active'),
    (2, 'PRJ-1002', 1, 'Data Warehouse Refresh', 'Improve analytics data pipelines and warehouse reliability.', '2024-09-02', '2025-06-30', 'Completed'),
    (3, 'PRJ-1003', 2, 'Employee Onboarding Program', 'Standardize onboarding workflows and employee resources.', '2025-02-03', NULL, 'Active'),
    (4, 'PRJ-1004', 2, 'HRIS Upgrade', 'Upgrade the human resources information system.', '2025-07-01', '2025-12-15', 'Completed'),
    (5, 'PRJ-1005', 3, 'Budget Planning 2026', 'Coordinate annual budget planning and financial forecasts.', '2025-08-04', '2025-11-28', 'Completed'),
    (6, 'PRJ-1006', 3, 'Expense Automation', 'Automate expense review and reconciliation processes.', '2025-03-10', NULL, 'Active'),
    (7, 'PRJ-1007', 4, 'Brand Relaunch', 'Refresh brand identity and supporting campaign materials.', '2025-01-20', '2025-09-30', 'Completed'),
    (8, 'PRJ-1008', 4, 'Customer Insights Campaign', 'Deliver a data-informed customer engagement campaign.', '2025-05-12', NULL, 'Active'),
    (9, 'PRJ-1009', 5, 'Supply Chain Optimization', 'Reduce process delays across procurement and fulfillment.', '2025-04-07', NULL, 'Active'),
    (10, 'PRJ-1010', 5, 'Facilities Efficiency', 'Identify and implement facilities operating efficiencies.', '2025-09-01', NULL, 'OnHold');

INSERT INTO employee_projects
    (employee_id, project_id, project_role, allocation_percent, assigned_on, released_on)
VALUES
    (1, 1, 'Executive Sponsor', 10.00, '2025-01-06', NULL),
    (6, 1, 'Technical Lead', 50.00, '2025-01-06', NULL),
    (8, 1, 'Application Developer', 75.00, '2025-01-06', NULL),
    (9, 1, 'Quality Engineer', 50.00, '2025-01-13', NULL),
    (7, 2, 'Data Engineer', 80.00, '2024-09-02', '2025-06-30'),
    (6, 2, 'Platform Advisor', 20.00, '2024-09-02', '2025-06-30'),
    (2, 3, 'Executive Sponsor', 10.00, '2025-02-03', NULL),
    (10, 3, 'Program Lead', 40.00, '2025-02-03', NULL),
    (11, 3, 'Recruitment Advisor', 25.00, '2025-02-10', NULL),
    (12, 3, 'Process Specialist', 60.00, '2025-02-03', NULL),
    (10, 4, 'Business Lead', 30.00, '2025-07-01', '2025-12-15'),
    (12, 4, 'Implementation Specialist', 50.00, '2025-07-01', '2025-12-15'),
    (3, 5, 'Executive Sponsor', 10.00, '2025-08-04', '2025-11-28'),
    (13, 5, 'Planning Lead', 50.00, '2025-08-04', '2025-11-28'),
    (14, 5, 'Financial Analyst', 60.00, '2025-08-04', '2025-11-28'),
    (13, 6, 'Process Owner', 25.00, '2025-03-10', NULL),
    (15, 6, 'Automation Analyst', 50.00, '2025-03-10', NULL),
    (4, 7, 'Executive Sponsor', 10.00, '2025-01-20', '2025-09-30'),
    (16, 7, 'Campaign Lead', 50.00, '2025-01-20', '2025-09-30'),
    (17, 7, 'Content Strategist', 60.00, '2025-01-20', '2025-09-30'),
    (16, 8, 'Campaign Lead', 40.00, '2025-05-12', NULL),
    (18, 8, 'Insights Analyst', 60.00, '2025-05-12', NULL),
    (5, 9, 'Executive Sponsor', 10.00, '2025-04-07', NULL),
    (19, 9, 'Operations Lead', 50.00, '2025-04-07', NULL),
    (20, 9, 'Process Analyst', 70.00, '2025-04-07', NULL),
    (19, 10, 'Project Lead', 30.00, '2025-09-01', NULL),
    (20, 10, 'Efficiency Analyst', 40.00, '2025-09-01', NULL),
    (7, 1, 'Data Integration Engineer', 20.00, '2025-02-03', NULL),
    (14, 6, 'Financial Controls Advisor', 15.00, '2025-03-17', NULL),
    (18, 7, 'Campaign Analyst', 25.00, '2025-02-10', '2025-09-30');

COMMIT;
