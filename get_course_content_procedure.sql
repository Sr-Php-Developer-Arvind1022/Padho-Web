-- Update the usp_InsertCourseContent procedure to include questions_json parameter
DROP PROCEDURE IF EXISTS usp_InsertCourseContent;

DELIMITER $$

CREATE PROCEDURE usp_InsertCourseContent(
    IN p_course_id_fk INT,
    IN p_topic VARCHAR(255),
    IN p_description TEXT,
    IN p_video_path VARCHAR(500),
    IN p_assignment_path VARCHAR(500),
    IN p_questions_json LONGTEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Rollback in case of any error
        ROLLBACK;
        SELECT NULL AS course_contents_id_pk,
               'Error' AS Status,
               'An error occurred while inserting course content.' AS Message;
    END;

    START TRANSACTION;

    -- Simple validation: Required fields must not be empty
    IF p_course_id_fk IS NULL OR p_topic = '' OR p_video_path = '' THEN
        ROLLBACK;
        SELECT NULL AS course_contents_id_pk,
               'Validation Error' AS Status,
               'Course ID, Topic, and Video Path are required fields.' AS Message;
    ELSE
        -- Insert data
        INSERT INTO course_contents (
            course_id_fk,
            topic,
            description,
            video_path,
            assignment_path,
            questions_json,
            is_active,
            created_at,
            updated_at
        ) VALUES (
            p_course_id_fk,
            p_topic,
            p_description,
            p_video_path,
            p_assignment_path,
            p_questions_json,
            1,
            NOW(),
            NOW()
        );

        -- Commit transaction after successful insert
        COMMIT;

        -- Return success message with inserted ID
        SELECT 
            LAST_INSERT_ID() AS course_contents_id_pk,
            'Success' AS Status,
            'Course content uploaded successfully!' AS Message;
    END IF;
END$$

DELIMITER ;

-- Stored procedure to get course content by course_id_fk
DROP PROCEDURE IF EXISTS usp_GetCourseContent;

DELIMITER $$

CREATE PROCEDURE usp_GetCourseContent(
    IN p_course_id_fk INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Rollback in case of any error
        ROLLBACK;
        SELECT NULL AS course_contents_id_pk,
               'Error' AS Status,
               'An error occurred while fetching course content.' AS Message;
    END;

    -- Validation: Check if course_id_fk is provided
    IF p_course_id_fk IS NULL OR p_course_id_fk <= 0 THEN
        SELECT NULL AS course_contents_id_pk,
               'Validation Error' AS Status,
               'Valid Course ID is required.' AS Message;
    ELSE
        -- Fetch course content for the given course_id_fk
        SELECT 
            course_contents_id_pk,
            course_id_fk,
            topic,
            description,
            video_path,
            questions_json,
            assignment_path,
            is_active,
            created_at,
            updated_at,
            'Success' AS Status,
            'Course content retrieved successfully!' AS Message
        FROM course_contents 
        WHERE course_id_fk = p_course_id_fk 
        AND is_active = 1
        ORDER BY created_at ASC;
    END IF;
END$$

DELIMITER ;

-- Stored procedure to get specific course content by primary key
DROP PROCEDURE IF EXISTS usp_GetCourseContentById;

DELIMITER $$

CREATE PROCEDURE usp_GetCourseContentById(
    IN p_course_contents_id_pk INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Rollback in case of any error
        ROLLBACK;
        SELECT NULL AS course_contents_id_pk,
               'Error' AS Status,
               'An error occurred while fetching course content.' AS Message;
    END;

    -- Validation: Check if course_contents_id_pk is provided
    IF p_course_contents_id_pk IS NULL OR p_course_contents_id_pk <= 0 THEN
        SELECT NULL AS course_contents_id_pk,
               'Validation Error' AS Status,
               'Valid Course Content ID is required.' AS Message;
    ELSE
        -- Check if course content exists
        IF EXISTS (SELECT 1 FROM course_contents WHERE course_contents_id_pk = p_course_contents_id_pk AND is_active = 1) THEN
            -- Fetch specific course content
            SELECT 
                course_contents_id_pk,
                course_id_fk,
                topic,
                description,
                video_path,
                questions_json,
                assignment_path,
                is_active,
                created_at,
                updated_at,
                'Success' AS Status,
                'Course content retrieved successfully!' AS Message
            FROM course_contents 
            WHERE course_contents_id_pk = p_course_contents_id_pk 
            AND is_active = 1;
        ELSE
            SELECT NULL AS course_contents_id_pk,
                   'Not Found' AS Status,
                   'Course content not found or inactive.' AS Message;
        END IF;
    END IF;
END$$

DELIMITER ;