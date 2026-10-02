INSERT INTO courses (course_name, department, total_seats, seats_available, fees) VALUES
 ('B.E. Computer Science and Engineering', 'CSE', 60, 60, 85000),
 ('B.E. Electronics and Communication', 'ECE', 60, 60, 80000),
 ('B.E. Mechanical Engineering', 'MECH', 40, 40, 75000),
 ('B.E. Artificial Intelligence and Data Science', 'AI&DS', 60, 60, 90000),
 ('B.Tech Information Technology', 'IT', 40, 40, 85000);

INSERT INTO applicants (name, dob, gender, phone, email, cutoff_mark) VALUES
 ('Arun Kumar',       '2007-05-14', 'M', '9876543210', 'arun.kumar@example.com',   92.50),
 ('Priya Devi',       '2007-08-21', 'F', '9123456780', 'priya.devi@example.com',   78.25),
 ('Karthik Raja',     '2007-02-03', 'M', '9988776655', 'karthik.raja@example.com', 88.00),
 ('Divya Lakshmi',    '2007-11-30', 'F', '9876501234', 'divya.l@example.com',      95.75),
 ('Mohammed Irfan',   '2007-04-18', 'M', '9345678123', 'irfan.m@example.com',      81.40),
 ('Sneha R',          '2007-07-09', 'F', '9444012345', 'sneha.r@example.com',      69.90),
 ('Vignesh S',        '2007-01-25', 'M', '9600123456', 'vignesh.s@example.com',    85.60),
 ('Anitha M',         '2007-09-12', 'F', '9791234567', 'anitha.m@example.com',     90.10);

INSERT INTO applications (applicant_id, course_id, apply_date, status) VALUES
 (1, 1, date('now'), 'PENDING'),
 (2, 2, date('now'), 'PENDING'),
 (3, 4, date('now'), 'PENDING'),
 (4, 1, date('now'), 'PENDING'),
 (5, 4, date('now'), 'PENDING'),
 (6, 3, date('now'), 'PENDING'),
 (7, 5, date('now'), 'PENDING'),
 (8, 4, date('now'), 'PENDING');
