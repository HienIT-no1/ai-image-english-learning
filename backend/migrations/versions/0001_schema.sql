-- Legacy schema frozen from the supplied project SQL; no seed data or ownership commands.
CREATE TABLE public.collection_words (
    collection_word_id bigint NOT NULL,
    collection_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    image_id bigint,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE public.collection_words_collection_word_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.collection_words_collection_word_id_seq OWNED BY public.collection_words.collection_word_id;

CREATE TABLE public.collections (
    collection_id bigint NOT NULL,
    user_id bigint NOT NULL,
    collection_name character varying(100) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE public.collections_collection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.collections_collection_id_seq OWNED BY public.collections.collection_id;

CREATE TABLE public.images (
    image_id bigint NOT NULL,
    user_id bigint NOT NULL,
    image_url text NOT NULL,
    source_type character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT images_source_type_check CHECK (((source_type)::text = ANY ((ARRAY['CAMERA'::character varying, 'UPLOAD'::character varying])::text[])))
);

CREATE SEQUENCE public.images_image_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.images_image_id_seq OWNED BY public.images.image_id;

CREATE TABLE public.learning_progress (
    progress_id bigint NOT NULL,
    user_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    status character varying(20) DEFAULT 'NEW'::character varying NOT NULL,
    review_count integer DEFAULT 0 NOT NULL,
    correct_count integer DEFAULT 0 NOT NULL,
    incorrect_count integer DEFAULT 0 NOT NULL,
    last_reviewed_at timestamp with time zone,
    next_review_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT learning_progress_correct_count_check CHECK ((correct_count >= 0)),
    CONSTRAINT learning_progress_incorrect_count_check CHECK ((incorrect_count >= 0)),
    CONSTRAINT learning_progress_review_count_check CHECK ((review_count >= 0)),
    CONSTRAINT learning_progress_status_check CHECK (((status)::text = ANY ((ARRAY['NEW'::character varying, 'LEARNING'::character varying, 'REVIEWING'::character varying, 'MASTERED'::character varying])::text[])))
);

CREATE SEQUENCE public.learning_progress_progress_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.learning_progress_progress_id_seq OWNED BY public.learning_progress.progress_id;

CREATE TABLE public.quiz_answers (
    answer_id bigint NOT NULL,
    attempt_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    question_type character varying(30) NOT NULL,
    user_answer text,
    correct_answer text NOT NULL,
    is_correct boolean NOT NULL,
    answered_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT quiz_answers_question_type_check CHECK (((question_type)::text = ANY ((ARRAY['IMAGE_TO_WORD'::character varying, 'WORD_TO_IMAGE'::character varying, 'LISTENING'::character varying, 'FILL_BLANK'::character varying])::text[])))
);

CREATE SEQUENCE public.quiz_answers_answer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.quiz_answers_answer_id_seq OWNED BY public.quiz_answers.answer_id;

CREATE TABLE public.quiz_attempts (
    attempt_id bigint NOT NULL,
    user_id bigint NOT NULL,
    quiz_type character varying(30) NOT NULL,
    total_questions integer DEFAULT 0 NOT NULL,
    correct_answers integer DEFAULT 0 NOT NULL,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    CONSTRAINT quiz_attempts_check CHECK (((correct_answers >= 0) AND (correct_answers <= total_questions))),
    CONSTRAINT quiz_attempts_quiz_type_check CHECK (((quiz_type)::text = ANY ((ARRAY['IMAGE_TO_WORD'::character varying, 'WORD_TO_IMAGE'::character varying, 'LISTENING'::character varying, 'FILL_BLANK'::character varying, 'MIXED'::character varying])::text[]))),
    CONSTRAINT quiz_attempts_total_questions_check CHECK ((total_questions >= 0))
);

CREATE SEQUENCE public.quiz_attempts_attempt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.quiz_attempts_attempt_id_seq OWNED BY public.quiz_attempts.attempt_id;

CREATE TABLE public.users (
    user_id bigint NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(100),
    english_level character varying(20),
    daily_goal integer DEFAULT 10,
    current_streak integer DEFAULT 0,
    longest_streak integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_daily_goal_check CHECK ((daily_goal > 0)),
    CONSTRAINT users_english_level_check CHECK (((english_level)::text = ANY ((ARRAY['BEGINNER'::character varying, 'INTERMEDIATE'::character varying, 'ADVANCED'::character varying])::text[])))
);

CREATE SEQUENCE public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;

CREATE TABLE public.vocabularies (
    vocabulary_id bigint NOT NULL,
    word character varying(100) NOT NULL,
    ipa character varying(100),
    part_of_speech character varying(30),
    level character varying(20),
    audio_url text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT vocabularies_level_check CHECK (((level)::text = ANY ((ARRAY['BEGINNER'::character varying, 'INTERMEDIATE'::character varying, 'ADVANCED'::character varying])::text[])))
);

CREATE SEQUENCE public.vocabularies_vocabulary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.vocabularies_vocabulary_id_seq OWNED BY public.vocabularies.vocabulary_id;

CREATE TABLE public.vocabulary_examples (
    example_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    sentence_en text NOT NULL,
    sentence_vi text
);

CREATE SEQUENCE public.vocabulary_examples_example_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.vocabulary_examples_example_id_seq OWNED BY public.vocabulary_examples.example_id;

CREATE TABLE public.vocabulary_meanings (
    meaning_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    meaning_vi text NOT NULL,
    definition_en text
);

CREATE SEQUENCE public.vocabulary_meanings_meaning_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.vocabulary_meanings_meaning_id_seq OWNED BY public.vocabulary_meanings.meaning_id;

CREATE TABLE public.vocabulary_relations (
    relation_id bigint NOT NULL,
    vocabulary_id bigint NOT NULL,
    related_vocabulary_id bigint,
    related_text character varying(255),
    relation_type character varying(20) NOT NULL,
    CONSTRAINT vocabulary_relations_check CHECK (((related_vocabulary_id IS NOT NULL) OR (related_text IS NOT NULL))),
    CONSTRAINT vocabulary_relations_relation_type_check CHECK (((relation_type)::text = ANY ((ARRAY['SYNONYM'::character varying, 'ANTONYM'::character varying, 'COLLOCATION'::character varying])::text[])))
);

CREATE SEQUENCE public.vocabulary_relations_relation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.vocabulary_relations_relation_id_seq OWNED BY public.vocabulary_relations.relation_id;

ALTER TABLE ONLY public.collection_words ALTER COLUMN collection_word_id SET DEFAULT nextval('public.collection_words_collection_word_id_seq'::regclass);

ALTER TABLE ONLY public.collections ALTER COLUMN collection_id SET DEFAULT nextval('public.collections_collection_id_seq'::regclass);

ALTER TABLE ONLY public.images ALTER COLUMN image_id SET DEFAULT nextval('public.images_image_id_seq'::regclass);

ALTER TABLE ONLY public.learning_progress ALTER COLUMN progress_id SET DEFAULT nextval('public.learning_progress_progress_id_seq'::regclass);

ALTER TABLE ONLY public.quiz_answers ALTER COLUMN answer_id SET DEFAULT nextval('public.quiz_answers_answer_id_seq'::regclass);

ALTER TABLE ONLY public.quiz_attempts ALTER COLUMN attempt_id SET DEFAULT nextval('public.quiz_attempts_attempt_id_seq'::regclass);

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);

ALTER TABLE ONLY public.vocabularies ALTER COLUMN vocabulary_id SET DEFAULT nextval('public.vocabularies_vocabulary_id_seq'::regclass);

ALTER TABLE ONLY public.vocabulary_examples ALTER COLUMN example_id SET DEFAULT nextval('public.vocabulary_examples_example_id_seq'::regclass);

ALTER TABLE ONLY public.vocabulary_meanings ALTER COLUMN meaning_id SET DEFAULT nextval('public.vocabulary_meanings_meaning_id_seq'::regclass);

ALTER TABLE ONLY public.vocabulary_relations ALTER COLUMN relation_id SET DEFAULT nextval('public.vocabulary_relations_relation_id_seq'::regclass);

ALTER TABLE ONLY public.collection_words
    ADD CONSTRAINT collection_words_collection_id_vocabulary_id_key UNIQUE (collection_id, vocabulary_id);

ALTER TABLE ONLY public.collection_words
    ADD CONSTRAINT collection_words_pkey PRIMARY KEY (collection_word_id);

ALTER TABLE ONLY public.collections
    ADD CONSTRAINT collections_pkey PRIMARY KEY (collection_id);

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (image_id);

ALTER TABLE ONLY public.learning_progress
    ADD CONSTRAINT learning_progress_pkey PRIMARY KEY (progress_id);

ALTER TABLE ONLY public.learning_progress
    ADD CONSTRAINT learning_progress_user_id_vocabulary_id_key UNIQUE (user_id, vocabulary_id);

ALTER TABLE ONLY public.quiz_answers
    ADD CONSTRAINT quiz_answers_pkey PRIMARY KEY (answer_id);

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_pkey PRIMARY KEY (attempt_id);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);

ALTER TABLE ONLY public.vocabularies
    ADD CONSTRAINT vocabularies_pkey PRIMARY KEY (vocabulary_id);

ALTER TABLE ONLY public.vocabularies
    ADD CONSTRAINT vocabularies_word_key UNIQUE (word);

ALTER TABLE ONLY public.vocabulary_examples
    ADD CONSTRAINT vocabulary_examples_pkey PRIMARY KEY (example_id);

ALTER TABLE ONLY public.vocabulary_meanings
    ADD CONSTRAINT vocabulary_meanings_pkey PRIMARY KEY (meaning_id);

ALTER TABLE ONLY public.vocabulary_relations
    ADD CONSTRAINT vocabulary_relations_pkey PRIMARY KEY (relation_id);

ALTER TABLE ONLY public.collection_words
    ADD CONSTRAINT collection_words_collection_id_fkey FOREIGN KEY (collection_id) REFERENCES public.collections(collection_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.collection_words
    ADD CONSTRAINT collection_words_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.images(image_id) ON DELETE SET NULL;

ALTER TABLE ONLY public.collection_words
    ADD CONSTRAINT collection_words_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.collections
    ADD CONSTRAINT collections_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_progress
    ADD CONSTRAINT learning_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_progress
    ADD CONSTRAINT learning_progress_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.quiz_answers
    ADD CONSTRAINT quiz_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.quiz_attempts(attempt_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.quiz_answers
    ADD CONSTRAINT quiz_answers_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.vocabulary_examples
    ADD CONSTRAINT vocabulary_examples_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.vocabulary_meanings
    ADD CONSTRAINT vocabulary_meanings_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.vocabulary_relations
    ADD CONSTRAINT vocabulary_relations_related_vocabulary_id_fkey FOREIGN KEY (related_vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.vocabulary_relations
    ADD CONSTRAINT vocabulary_relations_vocabulary_id_fkey FOREIGN KEY (vocabulary_id) REFERENCES public.vocabularies(vocabulary_id) ON DELETE CASCADE;
