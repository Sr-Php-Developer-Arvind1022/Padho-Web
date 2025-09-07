-- Create missing stored procedures for course operations

-- 1. Get Course by ID
DROP PROCEDURE IF EXISTS usp_GetCourseById;

DELIMITER $$

CREATE PROCEDURE usp_GetCourseById(
    IN p_course_id INT,
    IN p_login_id_fk INT
)
BEGIN
    DECLARE course_count INT DEFAULT 0;
    
    -- Validate parameters
    IF p_course_id IS NULL OR p_course_id <= 0 THEN
        SELECT 'Course ID is required and must be valid' as Message;
    ELSEIF p_login_id_fk IS NULL OR p_login_id_fk <= 0 THEN
        SELECT 'User authentication is required' as Message;
    ELSE
        -- Check if course exists and is active
        SELECT COUNT(*) INTO course_count 
        FROM courses 
        WHERE course_id_pk = p_course_id AND status = 'active';
        
        IF course_count = 0 THEN
            SELECT 'Course not found or inactive' as Message;
        ELSE
            -- Return course data
            SELECT 
                c.course_id_pk as course_id,
                c.course_name,
                c.course_title,
                c.course_description,
                c.course_price,
                c.course_image,
                c.demo_video,
                c.login_id_fk,
                c.status,
                c.created_at,
                c.updated_at,
                l.username as creator_email,
                l.role as creator_role
            FROM courses c
            LEFT JOIN logins l ON c.login_id_fk = l.login_id_pk
            WHERE c.course_id_pk = p_course_id 
            AND c.status = 'active'
            LIMIT 1;
        END IF;
    END IF;
END$$

DELIMITER ;

-- 2. Get All Courses (basic)
DROP PROCEDURE IF EXISTS usp_GetAllCourses;

DELIMITER $$

CREATE PROCEDURE usp_GetAllCourses()
BEGIN
    SELECT 
        c.course_id_pk as course_id,
        c.course_name,
        c.course_title,
        c.course_description,
        c.course_price,
        c.course_image,
        c.demo_video,
        c.login_id_fk,
        c.status,
        c.created_at,
        c.updated_at,
        l.username as creator_email,
        l.role as creator_role
    FROM courses c
    LEFT JOIN logins l ON c.login_id_fk = l.login_id_pk
    WHERE c.status = 'active'
    ORDER BY c.created_at DESC;
END$$

DELIMITER ;

-- 3. Get Courses by User
DROP PROCEDURE IF EXISTS usp_GetCoursesByUser;

DELIMITER $$

CREATE PROCEDURE usp_GetCoursesByUser(
    IN p_login_id_fk INT
)
BEGIN
    DECLARE course_count INT DEFAULT 0;
    
    -- Check if user exists
    SELECT COUNT(*) INTO course_count 
    FROM logins 
    WHERE login_id_pk = p_login_id_fk;
    
    IF course_count = 0 THEN
        SELECT 'User not found' as Message;
    ELSE
        -- Get courses for this user
        SELECT 
            c.course_id_pk as course_id,
            c.course_name,
            c.course_title,
            c.course_description,
            c.course_price,
            c.course_image,
            c.demo_video,
            c.login_id_fk,
            c.status,
            c.created_at,
            c.updated_at,
            l.username as creator_email,
            l.role as creator_role,
            CONCAT(l.username) as creator_name
        FROM courses c
        LEFT JOIN logins l ON c.login_id_fk = l.login_id_pk
        WHERE c.login_id_fk = p_login_id_fk 
        AND c.status = 'active'
        ORDER BY c.created_at DESC;
    END IF;
END$$

DELIMITER ;

-- 4. Course Registration Procedure
DROP PROCEDURE IF EXISTS usp_CourseRegister;

DELIMITER $$

CREATE PROCEDURE usp_CourseRegister(
    IN p_course_name VARCHAR(255),
    IN p_course_title VARCHAR(255),
    IN p_course_description TEXT,
    IN p_course_price DECIMAL(10,2),
    IN p_course_image VARCHAR(500),
    IN p_demo_video VARCHAR(500),
    IN p_login_id_fk INT
)
BEGIN
    DECLARE user_exists INT DEFAULT 0;
    DECLARE new_course_id INT;
    
    -- Check if user exists
    SELECT COUNT(*) INTO user_exists 
    FROM logins 
    WHERE login_id_pk = p_login_id_fk;
    
    IF user_exists = 0 THEN
        SELECT 'Error' as Status, 'User not found' as Message, NULL as course_id;
    ELSE
        -- Insert new course
        INSERT INTO courses (
            course_name, 
            course_title, 
            course_description, 
            course_price, 
            course_image, 
            demo_video, 
            login_id_fk, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            p_course_name,
            p_course_title,
            p_course_description,
            p_course_price,
            p_course_image,
            p_demo_video,
            p_login_id_fk,
            'active',
            NOW(),
            NOW()
        );
        
        SET new_course_id = LAST_INSERT_ID();
        
        SELECT 'Success' as Status, 'Course registered successfully' as Message, new_course_id as course_id;
    END IF;
END$$

DELIMITER ;

-- 5. Update Course by Login ID
DROP PROCEDURE IF EXISTS usp_UpdateCourseByLoginId;

DELIMITER $$

CREATE PROCEDURE usp_UpdateCourseByLoginId(
    IN p_course_id INT,
    IN p_login_id_fk INT,
    IN p_course_name VARCHAR(255),
    IN p_course_title VARCHAR(255),
    IN p_course_description TEXT,
    IN p_course_price DECIMAL(10,2),
    IN p_course_image VARCHAR(500),
    IN p_demo_video VARCHAR(500)
)
BEGIN
    DECLARE course_exists INT DEFAULT 0;
    DECLARE is_owner INT DEFAULT 0;
    
    -- Check if course exists
    SELECT COUNT(*) INTO course_exists 
    FROM courses 
    WHERE course_id_pk = p_course_id AND status = 'active';
    
    IF course_exists = 0 THEN
        SELECT 'Error' as Status, 'Course not found' as Message;
    ELSE
        -- Check if user is the owner of this course
        SELECT COUNT(*) INTO is_owner 
        FROM courses 
        WHERE course_id_pk = p_course_id AND login_id_fk = p_login_id_fk AND status = 'active';
        
        IF is_owner = 0 THEN
            SELECT 'Error' as Status, 'You are not authorized to update this course' as Message;
        ELSE
            -- Update course
            UPDATE courses 
            SET 
                course_name = COALESCE(p_course_name, course_name),
                course_title = COALESCE(p_course_title, course_title),
                course_description = COALESCE(p_course_description, course_description),
                course_price = COALESCE(p_course_price, course_price),
                course_image = COALESCE(p_course_image, course_image),
                demo_video = COALESCE(p_demo_video, demo_video),
                updated_at = NOW()
            WHERE course_id_pk = p_course_id;
            
            SELECT 'Success' as Status, 'Course updated successfully' as Message;
        END IF;
    END IF;
END$$

DELIMITER ;

-- 6. Get Courses for Public Access with Advanced Filtering
DROP PROCEDURE IF EXISTS usp_GetCoursesPublic;

DELIMITER $$

CREATE PROCEDURE usp_GetCoursesPublic(
    IN p_course_id INT,
    IN p_search VARCHAR(255),
    IN p_category_id INT,
    IN p_sort_by VARCHAR(50),
    IN p_sort_order VARCHAR(10),
    IN p_limit INT,
    IN p_offset INT,
    IN p_min_price DECIMAL(10,2),
    IN p_max_price DECIMAL(10,2),
    IN p_status VARCHAR(20)
)
BEGIN
    DECLARE v_error_message VARCHAR(255) DEFAULT '';
    DECLARE v_sql_statement TEXT;
    DECLARE v_where_clause TEXT DEFAULT '';
    DECLARE v_order_clause TEXT DEFAULT '';
    
    -- Validation
    IF p_limit IS NULL OR p_limit <= 0 THEN
        SET p_limit = 10;
    END IF;
    
    IF p_offset IS NULL OR p_offset < 0 THEN
        SET p_offset = 0;
    END IF;
    
    -- Validate sort order
    IF p_sort_order IS NULL OR (p_sort_order NOT IN ('asc', 'desc', 'ASC', 'DESC')) THEN
        SET p_sort_order = 'desc';
    END IF;
    
    -- Validate sort by field
    IF p_sort_by IS NULL OR p_sort_by NOT IN ('course_name', 'course_title', 'course_price', 'created_at', 'updated_at') THEN
        SET p_sort_by = 'created_at';
    END IF;
    
    -- Validate status
    IF p_status IS NULL OR p_status = '' THEN
        SET p_status = 'active';
    END IF;
    
    -- Build base query with JOIN for creator info
    SET v_sql_statement = '
    SELECT 
        c.course_id_pk as course_id,
        c.course_name,
        c.course_title, 
        c.course_description,
        c.course_price,
        c.course_image,
        c.demo_video,
        c.login_id_fk,
        u.email as creator_email,
        u.role as creator_role,
        c.created_at,
        c.updated_at,
        c.status,
        c.category_id,
        cat.category_name
    FROM courses c
    LEFT JOIN users u ON c.login_id_fk = u.login_id_pk
    LEFT JOIN categories cat ON c.category_id = cat.category_id
    ';
    
    -- Build WHERE clause
    SET v_where_clause = ' WHERE 1=1 ';
    
    -- Filter by course_id if provided
    IF p_course_id IS NOT NULL AND p_course_id > 0 THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND c.course_id_pk = ', p_course_id);
    END IF;
    
    -- Filter by status
    IF p_status IS NOT NULL AND p_status != '' THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND c.status = ''', p_status, '''');
    END IF;
    
    -- Search functionality
    IF p_search IS NOT NULL AND TRIM(p_search) != '' AND TRIM(p_search) != 'none' THEN
        SET v_where_clause = CONCAT(v_where_clause, 
            ' AND (c.course_name LIKE ''%', TRIM(p_search), '%''',
            ' OR c.course_title LIKE ''%', TRIM(p_search), '%''',
            ' OR c.course_description LIKE ''%', TRIM(p_search), '%'')');
    END IF;
    
    -- Category filter
    IF p_category_id IS NOT NULL AND p_category_id > 0 THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND c.category_id = ', p_category_id);
    END IF;
    
    -- Price range filter
    IF p_min_price IS NOT NULL THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND c.course_price >= ', p_min_price);
    END IF;
    
    IF p_max_price IS NOT NULL THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND c.course_price <= ', p_max_price);
    END IF;
    
    -- Build ORDER BY clause
    SET v_order_clause = CONCAT(' ORDER BY c.', p_sort_by, ' ', UPPER(p_sort_order));
    
    -- Add LIMIT and OFFSET
    SET v_order_clause = CONCAT(v_order_clause, ' LIMIT ', p_limit, ' OFFSET ', p_offset);
    
    -- Combine all parts
    SET v_sql_statement = CONCAT(v_sql_statement, v_where_clause, v_order_clause);
    
    -- Execute dynamic query
    SET @sql = v_sql_statement;
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    
END$$

DELIMITER ;

-- 7. Create Course Order
DROP PROCEDURE IF EXISTS usp_CreateCourseOrder;

DELIMITER $$

CREATE PROCEDURE usp_CreateCourseOrder(
    IN p_course_id INT,
    IN p_login_id_fk INT,
    IN p_order_amount DECIMAL(10,2),
    IN p_payment_method VARCHAR(50),
    IN p_transaction_id VARCHAR(100)
)
procedure_block: BEGIN
    DECLARE v_error_message VARCHAR(255) DEFAULT '';
    DECLARE v_course_exists INT DEFAULT 0;
    DECLARE v_user_exists INT DEFAULT 0;
    DECLARE v_duplicate_order INT DEFAULT 0;
    DECLARE v_course_price DECIMAL(10,2) DEFAULT 0;
    DECLARE new_order_id INT DEFAULT 0;
    
    -- Validate inputs
    IF p_course_id IS NULL OR p_course_id <= 0 THEN
        SELECT 'Error' as Status, 'Invalid course ID provided' as Message;
        LEAVE procedure_block;
    END IF;
    
    IF p_login_id_fk IS NULL OR p_login_id_fk <= 0 THEN
        SELECT 'Error' as Status, 'Invalid login ID provided' as Message;
        LEAVE procedure_block;
    END IF;
    
    IF p_order_amount IS NULL OR p_order_amount <= 0 THEN
        SELECT 'Error' as Status, 'Invalid order amount provided' as Message;
        LEAVE procedure_block;
    END IF;
    
    -- Check if course exists and is active
    SELECT COUNT(*), course_price INTO v_course_exists, v_course_price
    FROM courses 
    WHERE course_id_pk = p_course_id AND status = 'active';
    
    IF v_course_exists = 0 THEN
        SELECT 'Error' as Status, 'Course not found or inactive' as Message;
        LEAVE procedure_block;
    END IF;
    
    -- Check if user exists
    SELECT COUNT(*) INTO v_user_exists
    FROM users 
    WHERE login_id_pk = p_login_id_fk;
    
    IF v_user_exists = 0 THEN
        SELECT 'Error' as Status, 'User not found' as Message;
        LEAVE procedure_block;
    END IF;
    
    -- Verify order amount matches course price
    IF ABS(p_order_amount - v_course_price) > 0.01 THEN
        SELECT 'Error' as Status, 'Order amount does not match course price' as Message;
        LEAVE procedure_block;
    END IF;
    
    -- Check for duplicate pending/completed orders
    SELECT COUNT(*) INTO v_duplicate_order
    FROM course_order 
    WHERE course_id_fk = p_course_id 
    AND login_id_fk = p_login_id_fk 
    AND order_status IN ('pending-verification', 'approved');
    
    IF v_duplicate_order > 0 THEN
        SELECT 'Error' as Status, 'Order already exists for this course' as Message;
        LEAVE procedure_block;
    END IF;
    
    -- Create new order
    INSERT INTO course_order (
        course_id_fk,
        login_id_fk,
        order_date,
        order_amount,
        payment_status,
        payment_method,
        transaction_id,
        order_status,
        created_at
    ) VALUES (
        p_course_id,
        p_login_id_fk,
        NOW(),
        p_order_amount,
        'pending',
        p_payment_method,
        p_transaction_id,
        'pending-verification',
        NOW()
    );
    
    SET new_order_id = LAST_INSERT_ID();
    
    SELECT 
        'Success' as Status,
        'Course order created successfully' as Message,
        new_order_id as order_id_pk,
        p_course_id as course_id_fk,
        p_login_id_fk as login_id_fk,
        NOW() as order_date,
        p_order_amount as order_amount,
        'pending' as payment_status,
        p_payment_method as payment_method,
        p_transaction_id as transaction_id,
        'pending-verification' as order_status,
        NOW() as created_at,
        NULL as updated_at;
    
END$$

DELIMITER ;

-- 8. Get Course Orders with Filters
DROP PROCEDURE IF EXISTS usp_GetCourseOrders;

DELIMITER $$

CREATE PROCEDURE usp_GetCourseOrders(
    IN p_order_id INT,
    IN p_course_id INT,
    IN p_login_id_fk INT,
    IN p_payment_status VARCHAR(20),
    IN p_order_status VARCHAR(30),
    IN p_start_date DATETIME,
    IN p_end_date DATETIME,
    IN p_limit INT,
    IN p_offset INT
)
BEGIN
    DECLARE v_sql_statement TEXT;
    DECLARE v_where_clause TEXT DEFAULT '';
    DECLARE v_order_clause TEXT DEFAULT '';
    
    -- Validation
    IF p_limit IS NULL OR p_limit <= 0 THEN
        SET p_limit = 10;
    END IF;
    
    IF p_offset IS NULL OR p_offset < 0 THEN
        SET p_offset = 0;
    END IF;
    
    -- Build base query
    SET v_sql_statement = '
    SELECT 
        co.order_id_pk,
        co.course_id_fk,
        co.login_id_fk,
        co.order_date,
        co.order_amount,
        co.payment_status,
        co.payment_method,
        co.transaction_id,
        co.order_status,
        co.created_at,
        co.updated_at,
        c.course_name,
        c.course_title,
        u.email as user_email
    FROM course_order co
    LEFT JOIN courses c ON co.course_id_fk = c.course_id_pk
    LEFT JOIN users u ON co.login_id_fk = u.login_id_pk
    ';
    
    -- Build WHERE clause
    SET v_where_clause = ' WHERE 1=1 ';
    
    -- Filter by order_id
    IF p_order_id IS NOT NULL AND p_order_id > 0 THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.order_id_pk = ', p_order_id);
    END IF;
    
    -- Filter by course_id
    IF p_course_id IS NOT NULL AND p_course_id > 0 THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.course_id_fk = ', p_course_id);
    END IF;
    
    -- Filter by login_id_fk
    IF p_login_id_fk IS NOT NULL AND p_login_id_fk > 0 THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.login_id_fk = ', p_login_id_fk);
    END IF;
    
    -- Filter by payment status
    IF p_payment_status IS NOT NULL AND p_payment_status != '' THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.payment_status = ''', p_payment_status, '''');
    END IF;
    
    -- Filter by order status
    IF p_order_status IS NOT NULL AND p_order_status != '' THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.order_status = ''', p_order_status, '''');
    END IF;
    
    -- Filter by date range
    IF p_start_date IS NOT NULL THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.order_date >= ''', p_start_date, '''');
    END IF;
    
    IF p_end_date IS NOT NULL THEN
        SET v_where_clause = CONCAT(v_where_clause, ' AND co.order_date <= ''', p_end_date, '''');
    END IF;
    
    -- Order by most recent first
    SET v_order_clause = ' ORDER BY co.created_at DESC';
    
    -- Add LIMIT and OFFSET
    SET v_order_clause = CONCAT(v_order_clause, ' LIMIT ', p_limit, ' OFFSET ', p_offset);
    
    -- Combine all parts
    SET v_sql_statement = CONCAT(v_sql_statement, v_where_clause, v_order_clause);
    
    -- Execute dynamic query
    SET @sql = v_sql_statement;
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    
END$$

DELIMITER ;
