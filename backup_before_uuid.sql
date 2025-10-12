--
-- PostgreSQL database dump
--

\restrict jVAb4Nc26owt4Gpu8vMR6cFonxi9TlAOlgeAp8NRIXqKZsanVQ0qvs9fwqzhMAB

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tenant_template; Type: SCHEMA; Schema: -; Owner: crewai
--

CREATE SCHEMA tenant_template;


ALTER SCHEMA tenant_template OWNER TO crewai;

--
-- Name: test_de28f32f; Type: SCHEMA; Schema: -; Owner: crewai
--

CREATE SCHEMA test_de28f32f;


ALTER SCHEMA test_de28f32f OWNER TO crewai;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: crewprocess; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.crewprocess AS ENUM (
    'SEQUENTIAL',
    'HIERARCHICAL'
);


ALTER TYPE public.crewprocess OWNER TO crewai;

--
-- Name: executionstatus; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.executionstatus AS ENUM (
    'PENDING',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED',
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled'
);


ALTER TYPE public.executionstatus OWNER TO crewai;

--
-- Name: executiontype; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.executiontype AS ENUM (
    'FLOW',
    'CREW',
    'agent',
    'tool',
    'task',
    'flow',
    'crew'
);


ALTER TYPE public.executiontype OWNER TO crewai;

--
-- Name: flowstatus; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.flowstatus AS ENUM (
    'DRAFT',
    'ACTIVE',
    'ARCHIVED'
);


ALTER TYPE public.flowstatus OWNER TO crewai;

--
-- Name: llmprovidertype; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.llmprovidertype AS ENUM (
    'OPENAI',
    'ANTHROPIC',
    'OLLAMA',
    'VLLM',
    'CUSTOM'
);


ALTER TYPE public.llmprovidertype OWNER TO crewai;

--
-- Name: taskoutputformat; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.taskoutputformat AS ENUM (
    'TEXT',
    'JSON',
    'PYDANTIC'
);


ALTER TYPE public.taskoutputformat OWNER TO crewai;

--
-- Name: tenantstatus; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.tenantstatus AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'DELETED'
);


ALTER TYPE public.tenantstatus OWNER TO crewai;

--
-- Name: tooltype; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.tooltype AS ENUM (
    'BUILTIN',
    'CUSTOM',
    'DOCKER'
);


ALTER TYPE public.tooltype OWNER TO crewai;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'MEMBER',
    'VIEWER'
);


ALTER TYPE public.userrole OWNER TO crewai;

--
-- Name: versionaction; Type: TYPE; Schema: public; Owner: crewai
--

CREATE TYPE public.versionaction AS ENUM (
    'CREATE',
    'UPDATE',
    'ROLLBACK'
);


ALTER TYPE public.versionaction OWNER TO crewai;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_tools; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.agent_tools (
    agent_id integer NOT NULL,
    tool_id integer NOT NULL
);


ALTER TABLE public.agent_tools OWNER TO crewai;

--
-- Name: agent_versions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.agent_versions (
    agent_id integer NOT NULL,
    version_number integer NOT NULL,
    action public.versionaction NOT NULL,
    changed_by_user_id integer,
    configuration json NOT NULL,
    diff_from_previous json,
    change_description text,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.agent_versions OWNER TO crewai;

--
-- Name: agent_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.agent_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_versions_id_seq OWNER TO crewai;

--
-- Name: agent_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.agent_versions_id_seq OWNED BY public.agent_versions.id;


--
-- Name: agents; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.agents (
    name character varying(255) NOT NULL,
    role character varying(255) NOT NULL,
    goal text NOT NULL,
    backstory text NOT NULL,
    llm_provider_id integer NOT NULL,
    temperature double precision NOT NULL,
    max_tokens integer,
    allow_delegation boolean NOT NULL,
    "verbose" boolean NOT NULL,
    cache boolean NOT NULL,
    max_iter integer NOT NULL,
    max_rpm integer,
    max_execution_time integer,
    allow_code_execution boolean NOT NULL,
    respect_context_window boolean NOT NULL,
    max_retry_limit integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.agents OWNER TO crewai;

--
-- Name: agents_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.agents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agents_id_seq OWNER TO crewai;

--
-- Name: agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.agents_id_seq OWNED BY public.agents.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO crewai;

--
-- Name: chat_folders; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.chat_folders (
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    name character varying(255) NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chat_folders OWNER TO crewai;

--
-- Name: chat_folders_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.chat_folders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chat_folders_id_seq OWNER TO crewai;

--
-- Name: chat_folders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.chat_folders_id_seq OWNED BY public.chat_folders.id;


--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.chat_sessions (
    user_id integer NOT NULL,
    title character varying(255),
    llm_provider_id integer NOT NULL,
    system_prompt text,
    is_active boolean NOT NULL,
    mongo_messages_collection character varying(255),
    folder_id integer,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chat_sessions OWNER TO crewai;

--
-- Name: chat_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.chat_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.chat_sessions_id_seq OWNER TO crewai;

--
-- Name: chat_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.chat_sessions_id_seq OWNED BY public.chat_sessions.id;


--
-- Name: crew_agents; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.crew_agents (
    crew_id integer NOT NULL,
    agent_id integer NOT NULL,
    "order" integer NOT NULL
);


ALTER TABLE public.crew_agents OWNER TO crewai;

--
-- Name: crews; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.crews (
    name character varying(255) NOT NULL,
    description text,
    process public.crewprocess NOT NULL,
    "verbose" boolean NOT NULL,
    memory boolean NOT NULL,
    manager_llm_provider_id integer,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.crews OWNER TO crewai;

--
-- Name: crews_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.crews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crews_id_seq OWNER TO crewai;

--
-- Name: crews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.crews_id_seq OWNED BY public.crews.id;


--
-- Name: executions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.executions (
    execution_type public.executiontype NOT NULL,
    status public.executionstatus NOT NULL,
    flow_id integer,
    crew_id integer,
    user_id integer NOT NULL,
    input_data json NOT NULL,
    output_data json,
    error text,
    mongo_log_id character varying(24),
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    agent_id integer,
    tool_id integer,
    task_id integer,
    execution_time_ms integer
);


ALTER TABLE public.executions OWNER TO crewai;

--
-- Name: executions_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.executions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.executions_id_seq OWNER TO crewai;

--
-- Name: executions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.executions_id_seq OWNED BY public.executions.id;


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.feedback (
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    feedback_type character varying(20) NOT NULL,
    execution_id integer,
    agent_id integer,
    chat_session_id character varying(255),
    rating integer NOT NULL,
    comment text,
    sentiment character varying(20),
    sentiment_score double precision,
    tags json NOT NULL,
    extra_data json NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.feedback OWNER TO crewai;

--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.feedback_id_seq OWNER TO crewai;

--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: flows; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.flows (
    name character varying(255) NOT NULL,
    description text,
    status public.flowstatus NOT NULL,
    nodes json NOT NULL,
    edges json NOT NULL,
    version integer NOT NULL,
    tags json NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.flows OWNER TO crewai;

--
-- Name: flows_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.flows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.flows_id_seq OWNER TO crewai;

--
-- Name: flows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.flows_id_seq OWNED BY public.flows.id;


--
-- Name: llm_providers; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.llm_providers (
    tenant_id integer NOT NULL,
    name character varying(255) NOT NULL,
    provider_type public.llmprovidertype NOT NULL,
    model_name character varying(255) NOT NULL,
    api_base character varying(255),
    api_key character varying(255),
    config json NOT NULL,
    is_active boolean NOT NULL,
    is_default boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.llm_providers OWNER TO crewai;

--
-- Name: llm_providers_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.llm_providers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.llm_providers_id_seq OWNER TO crewai;

--
-- Name: llm_providers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.llm_providers_id_seq OWNED BY public.llm_providers.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.notifications (
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    message text,
    data json,
    is_read boolean NOT NULL,
    read_at timestamp without time zone,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notifications OWNER TO crewai;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_id_seq OWNER TO crewai;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: prompt_categories; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_categories (
    id uuid NOT NULL,
    tenant_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    icon character varying(50),
    color character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_categories OWNER TO crewai;

--
-- Name: prompt_executions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_executions (
    id uuid NOT NULL,
    prompt_id uuid NOT NULL,
    user_id integer NOT NULL,
    tenant_id integer NOT NULL,
    context_type character varying(50) NOT NULL,
    context_id uuid,
    variables_used jsonb,
    model_used character varying(100),
    parameters_used jsonb,
    rendered_content text,
    execution_time_ms integer,
    success boolean,
    error_message text,
    user_satisfaction integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_executions OWNER TO crewai;

--
-- Name: prompt_favorites; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_favorites (
    id uuid NOT NULL,
    user_id integer NOT NULL,
    prompt_id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_favorites OWNER TO crewai;

--
-- Name: prompt_feedback; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_feedback (
    id uuid NOT NULL,
    prompt_id uuid NOT NULL,
    user_id integer NOT NULL,
    feedback_type character varying(50) NOT NULL,
    content text NOT NULL,
    is_resolved boolean,
    resolved_by integer,
    resolved_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_feedback OWNER TO crewai;

--
-- Name: prompt_ratings; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_ratings (
    id uuid NOT NULL,
    prompt_id uuid NOT NULL,
    user_id integer NOT NULL,
    rating integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_ratings OWNER TO crewai;

--
-- Name: prompt_templates; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_templates (
    id uuid NOT NULL,
    tenant_id integer NOT NULL,
    user_id integer NOT NULL,
    category_id uuid,
    name character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    description text,
    content text NOT NULL,
    suggested_model character varying(100),
    suggested_provider_id integer,
    default_temperature numeric(3,2),
    default_top_p numeric(3,2),
    default_top_k integer,
    default_max_tokens integer,
    default_frequency_penalty numeric(3,2),
    default_presence_penalty numeric(3,2),
    tags character varying[],
    variables jsonb,
    is_public boolean,
    is_active boolean,
    is_command_enabled boolean,
    version integer,
    parent_version_id uuid,
    usage_count integer,
    last_used_at timestamp without time zone,
    average_rating numeric(3,2),
    total_ratings integer,
    total_feedback integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_templates OWNER TO crewai;

--
-- Name: prompt_versions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.prompt_versions (
    id uuid NOT NULL,
    prompt_id uuid NOT NULL,
    version integer NOT NULL,
    content text NOT NULL,
    variables jsonb,
    model_params jsonb,
    change_summary text,
    created_by integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.prompt_versions OWNER TO crewai;

--
-- Name: provider_versions; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.provider_versions (
    provider_id integer NOT NULL,
    version_number integer NOT NULL,
    action public.versionaction NOT NULL,
    changed_by_user_id integer,
    configuration json NOT NULL,
    diff_from_previous json,
    change_description text,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.provider_versions OWNER TO crewai;

--
-- Name: provider_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.provider_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.provider_versions_id_seq OWNER TO crewai;

--
-- Name: provider_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.provider_versions_id_seq OWNED BY public.provider_versions.id;


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.tasks (
    name character varying(255) NOT NULL,
    description text NOT NULL,
    expected_output text NOT NULL,
    agent_id integer,
    crew_id integer,
    "order" integer NOT NULL,
    async_execution boolean NOT NULL,
    output_format public.taskoutputformat NOT NULL,
    output_file character varying(500),
    context text,
    tools_config text,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    variables json
);


ALTER TABLE public.tasks OWNER TO crewai;

--
-- Name: tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tasks_id_seq OWNER TO crewai;

--
-- Name: tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.tenants (
    name character varying(255) NOT NULL,
    schema_name character varying(63) NOT NULL,
    status public.tenantstatus NOT NULL,
    api_key character varying(255) NOT NULL,
    max_users integer NOT NULL,
    max_agents integer NOT NULL,
    max_flows integer NOT NULL,
    settings json NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tenants OWNER TO crewai;

--
-- Name: tenants_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.tenants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tenants_id_seq OWNER TO crewai;

--
-- Name: tenants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.tenants_id_seq OWNED BY public.tenants.id;


--
-- Name: tools; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.tools (
    name character varying(255) NOT NULL,
    description text NOT NULL,
    tool_type public.tooltype NOT NULL,
    code text,
    docker_image character varying(255),
    docker_command character varying(255),
    schema json NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tools OWNER TO crewai;

--
-- Name: tools_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.tools_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tools_id_seq OWNER TO crewai;

--
-- Name: tools_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.tools_id_seq OWNED BY public.tools.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: crewai
--

CREATE TABLE public.users (
    tenant_id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    role public.userrole NOT NULL,
    is_active boolean NOT NULL,
    password_reset_token character varying(255),
    password_reset_expires timestamp without time zone,
    require_password_change boolean NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.users OWNER TO crewai;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: crewai
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO crewai;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: crewai
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: agent_versions id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_versions ALTER COLUMN id SET DEFAULT nextval('public.agent_versions_id_seq'::regclass);


--
-- Name: agents id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agents ALTER COLUMN id SET DEFAULT nextval('public.agents_id_seq'::regclass);


--
-- Name: chat_folders id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_folders ALTER COLUMN id SET DEFAULT nextval('public.chat_folders_id_seq'::regclass);


--
-- Name: chat_sessions id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_sessions ALTER COLUMN id SET DEFAULT nextval('public.chat_sessions_id_seq'::regclass);


--
-- Name: crews id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crews ALTER COLUMN id SET DEFAULT nextval('public.crews_id_seq'::regclass);


--
-- Name: executions id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions ALTER COLUMN id SET DEFAULT nextval('public.executions_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: flows id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.flows ALTER COLUMN id SET DEFAULT nextval('public.flows_id_seq'::regclass);


--
-- Name: llm_providers id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.llm_providers ALTER COLUMN id SET DEFAULT nextval('public.llm_providers_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: provider_versions id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.provider_versions ALTER COLUMN id SET DEFAULT nextval('public.provider_versions_id_seq'::regclass);


--
-- Name: tasks id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tasks ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);


--
-- Name: tenants id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tenants ALTER COLUMN id SET DEFAULT nextval('public.tenants_id_seq'::regclass);


--
-- Name: tools id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tools ALTER COLUMN id SET DEFAULT nextval('public.tools_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: agent_tools; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.agent_tools (agent_id, tool_id) FROM stdin;
3	2
\.


--
-- Data for Name: agent_versions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.agent_versions (agent_id, version_number, action, changed_by_user_id, configuration, diff_from_previous, change_description, id, created_at, updated_at) FROM stdin;
1	1	CREATE	\N	{"name": "Content Writer", "role": "Content Writer", "goal": "Write a comprehensive and thorough guide a bout specific topic", "backstory": "You have more than 15 years of experience in content writing specially technical content", "llm_provider_id": 1, "temperature": 0.7, "max_tokens": null, "allow_delegation": true, "verbose": false, "cache": true, "max_iter": 15, "max_rpm": null, "max_execution_time": null, "allow_code_execution": false, "respect_context_window": true, "max_retry_limit": 2}	null	Initial agent creation	1	2025-10-08 23:56:51.397304	2025-10-08 23:56:51.397307
2	1	CREATE	\N	{"name": "Content Reviewer", "role": "Content Review", "goal": "Review content generate by the content writer.", "backstory": "You have 20+ years of experience in content writing and reviewing.", "llm_provider_id": 1, "temperature": 0.7, "max_tokens": null, "allow_delegation": true, "verbose": false, "cache": true, "max_iter": 15, "max_rpm": null, "max_execution_time": null, "allow_code_execution": false, "respect_context_window": true, "max_retry_limit": 2}	null	Initial agent creation	2	2025-10-08 23:58:04.126822	2025-10-08 23:58:04.126826
\.


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.agents (name, role, goal, backstory, llm_provider_id, temperature, max_tokens, allow_delegation, "verbose", cache, max_iter, max_rpm, max_execution_time, allow_code_execution, respect_context_window, max_retry_limit, id, created_at, updated_at) FROM stdin;
Content Writer	Content Writer	Write a comprehensive and thorough guide a bout specific topic	You have more than 15 years of experience in content writing specially technical content	1	0.7	\N	t	f	t	15	\N	\N	f	t	2	1	2025-10-08 23:56:51.381448	2025-10-08 23:56:51.381452
Content Reviewer	Content Review	Review content generate by the content writer.	You have 20+ years of experience in content writing and reviewing.	1	0.7	\N	t	f	t	15	\N	\N	f	t	2	2	2025-10-08 23:58:04.120154	2025-10-08 23:58:04.120156
Research Analyst	Senior Research Analyst	Uncover cutting-edge developments and provide comprehensive research on given topics	You work at a leading tech think tank.\nYour expertise lies in identifying emerging trends and technologies.\nYou have a knack for dissecting complex data and presenting actionable insights.	3	0.7	\N	f	t	t	15	\N	\N	f	t	2	3	2025-10-09 00:07:49.172676	2025-10-09 00:07:49.172676
Travel Expert	Amazing Travel Concierge	Create the most amazing travel itineraries with budget and packing suggestions	Specialist in travel planning and logistics with\ndecades of experience. You have traveled to every corner of the world\nand know the best places to visit, eat, and stay.	3	0.7	\N	t	t	t	15	\N	\N	f	t	2	4	2025-10-09 00:07:49.1752	2025-10-09 00:07:49.175201
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.alembic_version (version_num) FROM stdin;
ccf2db223d72
\.


--
-- Data for Name: chat_folders; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.chat_folders (tenant_id, user_id, name, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: chat_sessions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.chat_sessions (user_id, title, llm_provider_id, system_prompt, is_active, mongo_messages_collection, folder_id, id, created_at, updated_at) FROM stdin;
1	hi	1	\N	f	\N	\N	1	2025-10-08 02:16:11.874251	2025-10-08 02:18:02.362858
1	tt	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- tt: tt	f	\N	\N	4	2025-10-08 09:28:09.501599	2025-10-08 10:52:20.242882
1	mysession	1	\N	f	\N	\N	3	2025-10-08 02:20:29.404167	2025-10-08 10:52:22.32187
1	tttz	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- tt: tt	f	\N	\N	7	2025-10-08 11:02:00.121408	2025-10-08 11:34:30.356334
1	helloz	1	\N	f	\N	\N	2	2025-10-08 02:20:22.683783	2025-10-08 12:50:58.423309
1	tt	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- tt: tt	f	\N	\N	5	2025-10-08 10:52:29.621455	2025-10-08 12:51:06.137658
1	ttt	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- tt: tt	f	\N	\N	6	2025-10-08 10:53:05.30298	2025-10-08 12:51:24.134654
1	hello	1	\N	t	\N	\N	8	2025-10-08 21:05:45.279014	2025-10-08 21:05:45.279017
1	calcz	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- Calculator: Perform mathematical calculations	t	\N	\N	9	2025-10-09 12:20:40.331733	2025-10-09 12:20:40.331735
1	test	1	\N	t	\N	\N	10	2025-10-09 21:18:07.395456	2025-10-09 21:18:07.395461
1	test-prompts	1	\N	t	\N	\N	11	2025-10-11 20:37:43.445008	2025-10-11 20:37:43.445013
1	asdas	1	\N	t	\N	\N	12	2025-10-11 21:02:54.436179	2025-10-11 21:02:54.436184
1	test-atools	1	You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n- Calculator: Perform mathematical calculations	t	\N	\N	13	2025-10-11 23:36:19.36583	2025-10-11 23:36:19.365833
\.


--
-- Data for Name: crew_agents; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.crew_agents (crew_id, agent_id, "order") FROM stdin;
1	2	0
1	1	0
2	3	0
2	1	0
3	1	0
3	2	0
4	1	0
\.


--
-- Data for Name: crews; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.crews (name, description, process, "verbose", memory, manager_llm_provider_id, id, created_at, updated_at) FROM stdin;
Content Team	Our content Team	SEQUENTIAL	f	f	\N	1	2025-10-09 00:00:07.715066	2025-10-09 00:00:07.715075
Research Team	A crew that researches topics and creates comprehensive content	SEQUENTIAL	t	t	3	2	2025-10-09 00:07:49.176924	2025-10-09 00:07:49.176925
Content Writing Team	Write content	SEQUENTIAL	f	f	\N	3	2025-10-10 19:41:58.835214	2025-10-10 19:41:58.83522
test writing	testing 	SEQUENTIAL	f	f	\N	4	2025-10-10 21:04:20.919619	2025-10-10 21:04:20.919638
\.


--
-- Data for Name: executions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.executions (execution_type, status, flow_id, crew_id, user_id, input_data, output_data, error, mongo_log_id, id, created_at, updated_at, agent_id, tool_id, task_id, execution_time_ms) FROM stdin;
agent	failed	\N	\N	1	{"task_id": 4, "variables": {"topic": "Fine-tuning Pipeline", "level": "advanced"}}	\N	litellm.APIConnectionError: OllamaException - [Errno 111] Connection refused	\N	10	2025-10-10 19:31:49.38381	2025-10-10 19:33:04.451066	1	\N	\N	75058
agent	failed	\N	\N	1	{"task_id": 4, "variables": {"topic": "Fine-tuning Pipeline", "level": "advanced"}}	\N	litellm.APIConnectionError: OllamaException - [Errno 111] Connection refused	\N	11	2025-10-10 19:33:12.104965	2025-10-10 19:34:27.15947	1	\N	\N	75047
agent	completed	\N	\N	1	{"task_id": 4, "variables": {"topic": "fine-tuning", "level": "advanced"}}	{"output": "Thought: I now can give a great answer.\\n\\n**Fine-Tuning: Mastering the Art of Advanced Optimization**\\n===========================================================\\n\\n### Outline\\n\\n1. **Introduction**: The Importance of Fine-Tuning\\n2. **The Concept of Fine-Tuning**: Understanding the Basics\\n3. **Preparation is Key**: Setting Up for Fine-Tuning Success\\n4. **Hyperparameter Tuning**: The Heart of Fine-Tuning\\n5. **Evaluation and Iteration**: Refining Your Model\\n6. **Advanced Techniques**: Pushing the Envelope with Hyperband, Bayesian Optimization, and More\\n7. **Conclusion**: Unlocking the Full Potential of Your Model\\n\\n### Introduction: The Importance of Fine-Tuning\\n\\nImagine you're a master chef, tasked with creating the perfect dish. You have all the ingredients, the skills, and the passion. But, just like any good chef knows, the secret to a truly exceptional meal lies not in following a recipe, but in fine-tuning the details. It's the same with machine learning models \\u2013 no matter how advanced they are, there's always room for improvement.\\n\\nFine-tuning is the process of adjusting the parameters of an existing model to better suit your specific needs. It's like taking that perfectly good dish and adding just the right amount of seasoning to bring out its full flavor. And in a world where machine learning models are increasingly sophisticated, fine-tuning is no longer optional \\u2013 it's essential.\\n\\n### The Concept of Fine-Tuning: Understanding the Basics\\n\\nAt its core, fine-tuning involves adjusting the hyperparameters of an existing model. Hyperparameters are like knobs on your kitchen stove \\u2013 turn one way and you get more of something; turn another and you get less. The key is to find just the right balance.\\n\\nThere are two main types of fine-tuning: parameter tuning and architecture search. Parameter tuning involves adjusting the weights, learning rates, or batch sizes within an existing model architecture. Architecture search, on the other hand, involves modifying the underlying structure of the model itself \\u2013 adding new layers, changing the number of neurons, or experimenting with different activation functions.\\n\\n### Preparation is Key: Setting Up for Fine-Tuning Success\\n\\nBefore you begin fine-tuning, it's essential to prepare your data and models. This includes:\\n\\n* **Data Preprocessing**: Cleaning, normalizing, and transforming your data into a format that works well with machine learning algorithms.\\n* **Model Selection**: Choosing the right model architecture for your specific task \\u2013 whether it's image classification, natural language processing, or something else entirely.\\n* **Hyperparameter Configuration**: Defining the range of hyperparameters to be tuned, as well as any constraints or penalties.\\n\\n### Hyperparameter Tuning: The Heart of Fine-Tuning\\n\\nHyperparameter tuning is at the heart of fine-tuning. It involves exploring a vast parameter space to find the optimal combination of hyperparameters that produce the best results. There are several techniques used for hyperparameter tuning, including:\\n\\n* **Grid Search**: Evaluating every possible combination of hyperparameters within a predefined grid.\\n* **Random Search**: Randomly sampling the hyperparameter space and evaluating each point.\\n* **Bayesian Optimization**: Using probabilistic models to search for the optimal hyperparameters.\\n\\n### Evaluation and Iteration: Refining Your Model\\n\\nFine-tuning is an iterative process. Once you've identified the optimal hyperparameters, it's essential to evaluate your model on a validation set to ensure it generalizes well to new data. This may involve:\\n\\n* **Performance Metrics**: Tracking metrics such as accuracy, precision, recall, F1 score, or mean squared error.\\n* **Model Evaluation**: Using techniques like cross-validation or walk-forward optimization to gauge the model's performance over time.\\n\\n### Advanced Techniques: Pushing the Envelope with Hyperband, Bayesian Optimization, and More\\n\\nFor those looking to push the boundaries of fine-tuning, several advanced techniques are available:\\n\\n* **Hyperband**: A more efficient variant of random search that uses a combination of random sampling and sequential evaluation.\\n* **Bayesian Optimization**: Using probabilistic models to search for the optimal hyperparameters.\\n* **Ensemble Methods**: Combining multiple models trained on different subsets of data or with different hyperparameter settings.\\n\\n### Conclusion: Unlocking the Full Potential of Your Model\\n\\nFine-tuning is an essential step in machine learning development \\u2013 no matter how advanced your model may be. By understanding the basics, preparing for success, and leveraging advanced techniques like Hyperband and Bayesian optimization, you can unlock the full potential of your model and create truly exceptional results.\\n\\nWith this comprehensive guide to fine-tuning at your disposal, you're ready to take on even the most challenging machine learning tasks. So go ahead \\u2013 get cooking!"}	\N	\N	12	2025-10-10 19:39:09.151528	2025-10-10 19:39:49.775216	1	\N	\N	40606
crew	completed	\N	4	1	{"variables": {"level": "LLM fine-tuning", "topic": "advanced"}}	{"output": "Thought: I now can give a great answer\\n\\n**Advanced Level LLM Fine-Tuning: A Comprehensive Guide**\\n====================================================================\\n\\nTable of Contents\\n-----------------\\n\\n1. [Introduction](#introduction)\\n2. [Understanding the Basics of LLM Fine-Tuning](#understanding-the-basics-of-llm-fine-tuning)\\n3. [Preparation for Fine-Tuning](#preparation-for-fine-tuning)\\n\\t* 3.1 [Data Collection and Preprocessing](#data-collection-and-preprocessing)\\n\\t* 3.2 [Model Selection and Configuration](#model-selection-and-configuration)\\n4. [Fine-Tuning Process](#fine-tuning-process)\\n\\t* 4.1 [Choosing the Right Loss Function](#choosing-the-right-loss-function)\\n\\t* 4.2 [Hyperparameter Tuning](#hyperparameter-tuning)\\n5. [Evaluation and Validation](#evaluation-and-validation)\\n6. [Advanced Techniques in LLM Fine-Tuning](#advanced-techniques-in-llm-fine-tuning)\\n\\t* 6.1 [Transfer Learning with Domain Adaptation](#transfer-learning-with-domain-adaptation)\\n\\t* 6.2 [Multitask Learning and Knowledge Distillation](#multitask-learning-and-knowledge-distillation)\\n7. [Conclusion](#conclusion)\\n\\n### Introduction\\n\\nOnce upon a time, in the world of natural language processing (NLP), there existed a magical realm where large language models (LLMs) reigned supreme. These models were capable of understanding human language with uncanny accuracy and generating text that was almost indistinguishable from written by humans.\\n\\nHowever, as powerful as these models were, they were not perfect. They needed to be fine-tuned on specific tasks and domains to achieve optimal performance. This is where the art of LLM fine-tuning comes into play \\u2013 a process that requires both science and magic.\\n\\nIn this guide, we will embark on a journey through the realm of advanced level LLM fine-tuning. We will explore the basics, preparation, fine-tuning process, evaluation, and validation, as well as some advanced techniques that will make you a master of the art.\\n\\n### Understanding the Basics of LLM Fine-Tuning\\n\\nLLMs are pre-trained models that have been trained on vast amounts of text data to learn the underlying patterns and structures of language. However, these models are not task-specific; they need to be fine-tuned on specific tasks and domains to achieve optimal performance.\\n\\nThe process of fine-tuning an LLM involves adjusting its weights and biases to fit a particular task or domain. This is achieved by training the model on a dataset that is relevant to the task at hand, using a specific loss function and hyperparameters.\\n\\n**Why Fine-Tune?**\\n\\nFine-tuning an LLM can significantly improve its performance on a specific task compared to using it as is. The benefits of fine-tuning include:\\n\\n* Improved accuracy: Fine-tuning allows the model to adapt to the specific nuances of the task at hand, leading to improved accuracy.\\n* Reduced overfitting: By adjusting the model's weights and biases, fine-tuning helps reduce overfitting and improves generalizability.\\n\\n### Preparation for Fine-Tuning\\n\\nBefore diving into the fine-tuning process, it is essential to prepare your data and model. This involves collecting and preprocessing the relevant dataset, selecting the right model configuration, and setting up the necessary infrastructure.\\n\\n#### Data Collection and Preprocessing\\n\\nThe first step in preparation is to collect a dataset that is relevant to the task at hand. This may involve scraping web pages, extracting text from documents, or creating synthetic data.\\n\\nOnce you have your dataset, it's essential to preprocess it by performing tasks such as:\\n\\n* Tokenization: Breaking down the text into individual words or tokens.\\n* Stopword removal: Removing common words like \\"the,\\" \\"and,\\" etc. that do not add significant value to the meaning of the text.\\n* Lemmatization: Converting words to their base form.\\n\\n#### Model Selection and Configuration\\n\\nThe next step is to select the right LLM model for your task. This involves choosing a model that has been pre-trained on a relevant dataset and selecting the correct configuration for your task.\\n\\nSome popular LLM models include:\\n\\n* BERT (Bidirectional Encoder Representations from Transformers)\\n* RoBERTa (Robustly Optimized BERT Pretraining Approach)\\n* XLNet (Extreme Language Modeling)\\n\\n### Fine-Tuning Process\\n\\nOnce you have prepared your data and model, it's time to fine-tune the LLM. This involves adjusting its weights and biases using a specific loss function and hyperparameters.\\n\\n#### Choosing the Right Loss Function\\n\\nThe choice of loss function depends on the task at hand. Some common loss functions include:\\n\\n* Cross-entropy: Used for classification tasks.\\n* Mean squared error (MSE): Used for regression tasks.\\n* Mean absolute error (MAE): Used for regression tasks.\\n\\n#### Hyperparameter Tuning\\n\\nHyperparameter tuning involves adjusting the model's hyperparameters, such as learning rate, batch size, and number of epochs. This is typically done using techniques like grid search or random search.\\n\\n### Evaluation and Validation\\n\\nOnce you have fine-tuned your LLM, it's essential to evaluate its performance on a validation dataset. This will give you an idea of how well the model performs on unseen data.\\n\\nSome common metrics for evaluating LLMs include:\\n\\n* Accuracy\\n* Precision\\n* Recall\\n* F1-score\\n\\n### Advanced Techniques in LLM Fine-Tuning\\n\\nAs you become more comfortable with fine-tuning, it's time to explore some advanced techniques that will take your models to the next level.\\n\\n#### Transfer Learning with Domain Adaptation\\n\\nTransfer learning involves using a pre-trained model as a starting point for your task. However, this can be limiting if the pre-trained model was not trained on data similar to your task.\\n\\nDomain adaptation addresses this issue by fine-tuning the pre-trained model on a dataset that is relevant to your task.\\n\\n#### Multitask Learning and Knowledge Distillation\\n\\nMultitask learning involves training a single model on multiple tasks simultaneously. This can improve performance by sharing knowledge between tasks.\\n\\nKnowledge distillation involves transferring knowledge from a larger model to a smaller one, typically using the output of the larger model as input for the smaller one.\\n\\n### Conclusion\\n\\nIn this comprehensive guide, we have explored the world of advanced level LLM fine-tuning. From understanding the basics to evaluating and validating your models, we have covered it all.\\n\\nWhether you are a seasoned NLP practitioner or just starting out, this guide will give you the knowledge and skills needed to become a master of LLM fine-tuning.\\n\\nSo go ahead, embark on this journey, and discover the magic of advanced level LLM fine-tuning.", "task_count": 1}	\N	\N	13	2025-10-10 21:29:55.955526	2025-10-10 21:30:58.097148	\N	\N	\N	62117
flow	failed	7	\N	1	{"inputs": {"topic": "fine-tuning", "depth": "advanced"}}	\N		\N	14	2025-10-11 12:08:32.847842	2025-10-11 12:08:32.875851	\N	\N	\N	\N
agent	completed	\N	\N	1	{"task_id": 4, "variables": {"topic": "Red Hat", "level": "beginner"}}	{"output": "Thought: I now can give a great answer\\n\\n# Red Hat: The Story of an Open Source Leader\\n==============================\\n\\n### Table of Contents\\n\\n* [What is Red Hat?](#what-is-red-hat)\\n* [History of Red Hat](#history-of-red-hat)\\n\\t+ [Early Days](#early-days)\\n\\t+ [Growing Pains](#growing-pains)\\n\\t+ [IPO and Expansion](#ipo-and-expansion)\\n* [Red Hat's Business Model](#red-hats-business-model)\\n\\t+ [Open-Source Software](#open-source-software)\\n\\t+ [Support and Services](#support-and-services)\\n* [Red Hat in the Market](#red-hat-in-the-market)\\n\\t+ [Competitors and Partnerships](#competitors-and-partnerships)\\n\\t+ [Challenges and Opportunities](#challenges-and-opportunities)\\n\\n## What is Red Hat?\\n\\nImagine a world where technology is not just about individual components, but about how they work together in harmony. This is the vision of Red Hat, a company that has been at the forefront of open-source innovation for over two decades.\\n\\nRed Hat is more than just a software company; it's a community-driven movement that seeks to democratize access to technology and empower users with choice and flexibility. Founded on the principles of collaboration and mutual benefit, Red Hat has grown into one of the largest and most respected names in the tech industry.\\n\\n## History of Red Hat\\n\\nRed Hat's story begins in 1993, when Bob Young and Marc Ewing founded the company as a small business selling software distributions based on the Linux operating system. Here's a brief look at the key milestones in Red Hat's history:\\n\\n### Early Days\\n\\nIn its early days, Red Hat focused on creating and selling customized versions of Linux for various industries and platforms. The company's first product, Red Hat Software, was launched in 1994 and quickly gained popularity among developers and system administrators.\\n\\nHowever, things didn't always go smoothly. In the mid-1990s, Red Hat faced significant competition from other Linux distributors, leading to a period of consolidation and restructuring.\\n\\n### Growing Pains\\n\\nAs the company grew, so did its ambitions. Red Hat expanded its product line to include software development tools, middleware solutions, and consulting services. This diversification strategy helped the company establish itself as a leading provider of open-source solutions for enterprises.\\n\\nBut with growth comes challenges. In 2000, Red Hat faced financial difficulties due to increased competition from other Linux vendors and declining sales. The company underwent significant restructuring efforts, including layoffs and cost-cutting measures.\\n\\n### IPO and Expansion\\n\\nDespite these challenges, Red Hat persevered and eventually turned the corner in 1999 when it went public with an initial public offering (IPO). This influx of capital allowed Red Hat to expand its operations, invest in research and development, and make strategic acquisitions.\\n\\nIn 2006, Red Hat acquired JBoss, a leading provider of open-source middleware solutions. This acquisition marked a significant milestone for the company, as it solidified Red Hat's position as a major player in the enterprise software market.\\n\\n## Red Hat's Business Model\\n\\nSo, how does Red Hat make money? Unlike traditional software companies that rely on licensing fees and per-seat pricing models, Red Hat operates under a unique business model based on open-source principles:\\n\\n### Open-Source Software\\n\\nRed Hat develops and maintains many of its products using the open-source methodology. This approach allows users to download, use, and modify the software freely, without incurring any licensing costs.\\n\\nHowever, Red Hat generates revenue by offering support and maintenance services for these open-source products. By providing high-quality support, Red Hat ensures that customers can rely on its solutions and adopt them with confidence.\\n\\n### Support and Services\\n\\nRed Hat's business model relies heavily on its support and services offerings. The company provides a range of services, including:\\n\\n* Subscription-based support and maintenance\\n* Consulting and professional services\\n* Training and certification programs\\n* Community engagement and advocacy\\n\\nBy offering these services, Red Hat creates a revenue stream that complements its open-source software offerings.\\n\\n## Red Hat in the Market\\n\\nRed Hat operates in a highly competitive market with many other players vying for share. Here's a look at some of the key competitors and partnerships:\\n\\n### Competitors and Partnerships\\n\\nSome of Red Hat's main competitors include:\\n\\n* Canonical (Ubuntu)\\n* SUSE\\n* Oracle (Linux)\\n\\nHowever, Red Hat has also formed strategic partnerships with various companies to enhance its offerings and expand its reach.\\n\\nFor example, in 2020, Red Hat partnered with Microsoft to integrate its Kubernetes-based container platform with Azure services. This partnership reflects the growing trend towards hybrid cloud adoption and highlights Red Hat's commitment to collaboration and innovation.\\n\\n### Challenges and Opportunities\\n\\nDespite its success, Red Hat faces several challenges in the market:\\n\\n* Intense competition from other open-source vendors\\n* Growing cybersecurity threats and regulatory compliance requirements\\n* Evolving customer needs and preferences\\n\\nHowever, these challenges also present opportunities for growth and innovation. As the demand for hybrid cloud solutions continues to rise, Red Hat is well-positioned to capitalize on this trend with its comprehensive suite of products and services.\\n\\nIn conclusion, Red Hat's story is one of perseverance, innovation, and collaboration. From its humble beginnings as a small Linux distributor to its current status as a leading provider of open-source solutions, Red Hat has consistently demonstrated its commitment to empowering users and driving technological progress."}	\N	\N	8	2025-10-10 12:05:27.414012	2025-10-10 12:06:16.88724	1	\N	\N	49455
crew	completed	\N	4	1	{"variables": {"level": "basket ball", "topic": "beginner"}}	{"output": "The final answer is this comprehensive guide, providing a detailed outline of what it takes to learn basketball from scratch, emphasizing storytelling techniques to keep readers engaged throughout their journey.", "task_count": 1}	\N	\N	15	2025-10-11 12:09:38.161901	2025-10-11 12:10:32.631844	\N	\N	\N	54447
crew	completed	\N	4	1	{"variables": {"level": "fine-tuning", "topic": "advanced"}}	{"output": "Thought: I now can give a great answer\\n\\n**Advanced Level Fine-Tuning: A Comprehensive Guide**\\n======================================================\\n\\n**Table of Contents**\\n-----------------\\n\\n1. [Introduction](#introduction)\\n2. [Why Fine-Tune?](#why-fine-tune)\\n3. [Preparation is Key](#preparation-is-key)\\n\\t* [Data Collection and Preprocessing](#data-collection-and-preprocessing)\\n\\t* [Model Selection and Configuration](#model-selection-and-configuration)\\n4. [Fine-Tuning Techniques](#fine-tuning-techniques)\\n\\t* [Transfer Learning](#transfer-learning)\\n\\t* [Weight Initialization](#weight-initialization)\\n\\t* [Learning Rate Scheduling](#learning-rate-scheduling)\\n5. [Advanced Fine-Tuning Strategies](#advanced-fine-tuning-strategies)\\n\\t* [Ensemble Methods](#ensemble-methods)\\n\\t* [Early Stopping and Regularization](#early-stopping-and-regularization)\\n6. [Evaluating Model Performance](#evaluating-model-performance)\\n7. [Conclusion](#conclusion)\\n\\n**Introduction**\\n---------------\\n\\nImagine you're an artist, and your canvas is a blank slate waiting to be filled with the perfect blend of colors. You've got a beautiful painting as inspiration, but it's not exactly what you envisioned for your masterpiece. In machine learning, this is where fine-tuning comes in \\u2013 a process that allows us to adapt pre-trained models to our specific needs and create something truly unique.\\n\\n**Why Fine-Tune?**\\n-----------------\\n\\nLet's say we've got a pre-trained model that excels at image classification tasks but underperforms on object detection. By fine-tuning, we can leverage the strengths of the original model while adjusting it to our particular problem. This not only saves time and resources but also yields better results.\\n\\n### Why Fine-Tune?\\n\\n*   **Improved Performance**: Fine-tuning allows us to adapt a pre-trained model to our specific task, potentially leading to significant improvements in performance.\\n*   **Efficient Use of Resources**: Rather than starting from scratch or training a model from the beginning, we can fine-tune an existing model to achieve better results with less computational power and data.\\n*   **Enhanced Customization**: Fine-tuning enables us to make adjustments that are tailored to our specific needs, leading to a more customized solution.\\n\\n**Preparation is Key**\\n----------------------\\n\\nBefore we dive into the nitty-gritty of fine-tuning, let's cover some essential groundwork. This involves collecting and preprocessing data, as well as selecting and configuring the right model for the task at hand.\\n\\n### Data Collection and Preprocessing\\n\\n*   **Data Quality**: Ensure that our dataset is accurate, complete, and free from noise.\\n*   **Data Augmentation**: Apply techniques like rotation, flipping, or color jittering to enhance the diversity of our data without requiring additional samples.\\n*   **Normalization**: Standardize features by scaling them to a common range (e.g., 0-1) for easier processing.\\n\\n### Model Selection and Configuration\\n\\n*   **Model Choice**: Select a model that's suitable for your task, taking into account factors like architecture, number of parameters, and training requirements.\\n*   **Hyperparameter Tuning**: Adjust hyperparameters such as learning rate, batch size, or number of epochs to optimize performance.\\n\\n**Fine-Tuning Techniques**\\n-------------------------\\n\\nNow that we've prepared our data and selected the right model, it's time to fine-tune. This involves applying various techniques to adapt the pre-trained model to our specific task.\\n\\n### Transfer Learning\\n\\n*   **Leveraging Knowledge**: Tap into the knowledge acquired by the pre-trained model on a related task.\\n*   **Adapting Weights**: Update the weights of the pre-trained model to suit your task.\\n\\n### Weight Initialization\\n\\n*   **Random Initialization**: Initialize weights randomly, which can lead to slower convergence but better generalization.\\n*   **Kaiming Initialization**: Use Kaiming initialization to optimize weight distribution for faster and more stable training.\\n\\n### Learning Rate Scheduling\\n\\n*   **Constant Learning Rate**: Maintain a constant learning rate throughout training.\\n*   **Learning Rate Decay**: Gradually decrease the learning rate to avoid oscillations and promote convergence.\\n\\n**Advanced Fine-Tuning Strategies**\\n-----------------------------------\\n\\nAs we progress in our fine-tuning journey, we'll explore more sophisticated strategies that can help us achieve better results.\\n\\n### Ensemble Methods\\n\\n*   **Combining Models**: Combine the predictions of multiple models using techniques like averaging or stacking.\\n*   **Weighted Averaging**: Assign different weights to each model based on their performance.\\n\\n### Early Stopping and Regularization\\n\\n*   **Early Stopping**: Monitor the validation loss and stop training when it starts to increase, preventing overfitting.\\n*   **Regularization Techniques**: Apply techniques like dropout or L1/L2 regularization to prevent overfitting.\\n\\n**Evaluating Model Performance**\\n------------------------------\\n\\nFine-tuning is just one part of the equation; we also need to evaluate our model's performance using metrics like accuracy, precision, recall, F1 score, and ROC-AUC.\\n\\n### Common Metrics\\n\\n*   **Accuracy**: Measure overall correctness.\\n*   **Precision**: Evaluate positive predictions' precision.\\n*   **Recall**: Assess true positives' recall.\\n*   **F1 Score**: Combine precision and recall for a balanced measure.\\n*   **ROC-AUC**: Plot the receiver operating characteristic (ROC) curve and evaluate the area under the curve (AUC).\\n\\n**Conclusion**\\n----------\\n\\nFine-tuning is an essential skill in machine learning that allows us to adapt pre-trained models to our specific tasks. By understanding fine-tuning techniques, strategies, and evaluation metrics, we can unlock better performance, efficiency, and customization.\\n\\nAs our artistic canvas becomes a masterpiece, so too will our fine-tuned model \\u2013 unique, tailored, and effective.", "task_count": 1}	\N	\N	16	2025-10-11 12:20:02.390437	2025-10-11 12:20:55.532467	\N	\N	\N	53118
flow	failed	7	\N	1	{"inputs": {}}	\N	'CrewFactory' object has no attribute 'create_agent_from_db'	\N	1	2025-10-09 09:37:48.787825	2025-10-09 09:37:48.806779	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "fine-tuning", "depth": "advanced"}}	\N	'CrewFactory' object has no attribute 'create_agent_from_db'	\N	2	2025-10-09 09:59:14.92834	2025-10-09 09:59:14.942477	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "fine tuning LLM", "depth": "advanced"}}	\N	cannot import name 'SerperDevTool' from 'crewai.tools' (/usr/local/lib/python3.11/site-packages/crewai/tools/__init__.py)	\N	3	2025-10-09 10:40:53.143493	2025-10-09 10:40:53.169485	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "llm fine-tuning", "depth": "advanced"}}	\N	Built-in tool not available in this CrewAI version: Web Search	\N	4	2025-10-09 10:47:24.798747	2025-10-09 10:47:24.826219	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "fine-tuning llms", "depth": "advanced"}}	\N	Built-in tool 'Web Search' not available in this CrewAI version. Available tools: []. Consider creating a custom tool instead.	\N	5	2025-10-09 10:52:46.403886	2025-10-09 10:52:46.429137	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "LLM fine-tuning", "depth": "advanced"}}	\N	Custom tool code must define a 'run' function	\N	6	2025-10-09 16:47:56.679143	2025-10-09 16:47:56.705769	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "llm fine-tuning", "depth": "advanced"}}	\N	Custom tool code must define a 'run' function	\N	7	2025-10-09 21:17:17.216068	2025-10-09 21:17:17.238001	\N	\N	\N	\N
crew	completed	\N	4	1	{"variables": {"level": "advanced", "topic": "LLM model alignment"}}	{"output": "Thought: I now can give a great answer \\n\\n**LLM Model Alignment: A Comprehensive Guide**\\n=====================================================\\n\\n**Table of Contents**\\n-----------------\\n\\n1. [Introduction](#introduction)\\n2. [The Challenge of LLM Alignment](#the-challenge-of-llm-alignment)\\n3. [Understanding the Problem Space](#understanding-the-problem-space)\\n4. [Alignment Objectives and Metrics](#alignment-objectives-and-metrics)\\n5. [Techniques for Aligning LLMs](#techniques-for-aligning-lms)\\n6. [Challenges and Limitations of Current Approaches](#challenges-and-limitations-of-current-approaches)\\n7. [Future Directions and Research Opportunities](#future-directions-and-research-opportunities)\\n\\n**Introduction**\\n---------------\\n\\nImagine a world where artificial intelligence surpasses human intelligence, but its goals are misaligned with humanity's values. This is the stuff of science fiction, or so we thought. The development of Large Language Models (LLMs) has brought us closer to this reality than ever before.\\n\\nLLMs are designed to process and generate human-like text based on input prompts. While they have revolutionized natural language processing (NLP), their capabilities also raise concerns about their potential misuse. As LLMs become increasingly sophisticated, there is an urgent need for alignment \\u2013 ensuring that these models' objectives align with humanity's values.\\n\\n### The Challenge of LLM Alignment\\n\\nLLMs are trained on vast amounts of text data, which can include biases, misinformation, and undesirable language patterns. When an LLM generates output based on this training data, it may reflect these imperfections. Moreover, the complexity of human language and cognition makes it challenging to define a clear set of objectives for aligning LLMs.\\n\\nConsider the example of a conversational AI designed to engage in discussions about politics. The model might be trained on vast amounts of text data, including biased or inflammatory content. As a result, its responses may reflect these biases, leading to undesirable outcomes.\\n\\n**Understanding the Problem Space**\\n---------------------------------\\n\\nTo tackle the challenge of LLM alignment, we must first understand the problem space. This involves identifying the key factors that contribute to misalignment and developing strategies to mitigate them.\\n\\n### Misalignment Factors\\n\\n*   **Bias**: LLMs can perpetuate biases present in their training data, leading to undesirable outcomes.\\n*   **Lack of Transparency**: The inner workings of LLMs are often opaque, making it difficult to understand how they arrive at certain conclusions.\\n*   **Misunderstanding Human Values**: LLMs may not fully comprehend human values and ethics, leading to misaligned objectives.\\n\\n**Alignment Objectives and Metrics**\\n---------------------------------\\n\\nTo align LLMs with humanity's values, we need to define clear objectives and metrics for evaluation. This involves identifying key performance indicators (KPIs) that reflect desirable outcomes.\\n\\n### Alignment Objectives\\n\\n*   **Value Alignment**: Ensure the model's objectives align with human values, such as fairness, transparency, and respect.\\n*   **Safety**: Prevent the model from causing harm or promoting undesirable outcomes.\\n*   **Utility**: Maximize the model's utility while minimizing its negative impact.\\n\\n**Techniques for Aligning LLMs**\\n------------------------------\\n\\nSeveral techniques can be employed to align LLMs with humanity's values. These include:\\n\\n### Value-Based Alignment\\n\\n*   **Reward Shaping**: Modify the model's reward function to prioritize desirable outcomes.\\n*   **Value Learning**: Train the model to learn human values through interactive feedback.\\n\\n### Safety and Utility Maximization\\n\\n*   **Risk Management**: Implement risk management strategies, such as robustness and security measures.\\n*   **Value-Utility Trade-offs**: Balance value alignment with utility maximization.\\n\\n**Challenges and Limitations of Current Approaches**\\n---------------------------------------------------\\n\\nWhile current approaches hold promise, they are not without challenges and limitations. These include:\\n\\n### Complexity\\n\\n*   **Model Complexity**: LLMs' complexity makes it challenging to align their objectives.\\n*   **Scalability**: Aligning large-scale LLMs requires significant computational resources.\\n\\n**Future Directions and Research Opportunities**\\n---------------------------------------------\\n\\nThe challenge of LLM alignment is far from over. Future research opportunities include:\\n\\n### Advanced Techniques\\n\\n*   **Causal Alignment**: Investigate the causal relationships between human values and LLM objectives.\\n*   **Transfer Learning**: Explore how to transfer knowledge about human values from one task to another.\\n\\nAs we push the boundaries of LLM development, it is essential that we prioritize alignment with humanity's values. By doing so, we can ensure that these powerful tools benefit society as a whole.\\n\\nIn conclusion, LLM model alignment is a complex and multifaceted challenge. It requires a deep understanding of human values, ethics, and cognition, as well as advanced techniques in NLP and AI. While the journey ahead is long and arduous, it is crucial that we tackle this challenge head-on to ensure the safe and beneficial deployment of LLMs.", "task_count": 1}	\N	\N	17	2025-10-11 12:24:16.222425	2025-10-11 12:24:59.643297	\N	\N	\N	43391
agent	failed	\N	\N	1	{"task_id": 4, "variables": {"topic": "Fine Tuning Pipeline", "level": "advanced"}}	\N	litellm.APIConnectionError: OllamaException - [Errno 111] Connection refused	\N	9	2025-10-10 19:29:45.216047	2025-10-10 19:31:00.347349	1	\N	\N	75093
flow	failed	7	\N	1	{"inputs": {"topic": "Preference Tuning", "depth": "advanced"}}	\N		\N	18	2025-10-11 12:26:10.599733	2025-10-11 12:26:10.619673	\N	\N	\N	\N
flow	failed	7	\N	1	{"inputs": {"topic": "preference tuning", "depth": "advanced"}}	\N		\N	19	2025-10-11 12:29:46.083191	2025-10-11 12:29:46.10503	\N	\N	\N	\N
\.


--
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.feedback (tenant_id, user_id, feedback_type, execution_id, agent_id, chat_session_id, rating, comment, sentiment, sentiment_score, tags, extra_data, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: flows; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.flows (name, description, status, nodes, edges, version, tags, id, created_at, updated_at) FROM stdin;
New Flow	A new workflow	ARCHIVED	[{"id": "node_1", "type": "agent", "position": {"x": 415.5316477895003, "y": 223.59999847412115}, "data": {"label": "Agent Node"}}, {"id": "node_2", "type": "input", "position": {"x": 376.712514387791, "y": -88.83688416364245}, "data": {"label": "Flow Input", "description": "Define input variables for this flow", "inputs": [{"name": "input_1", "type": "string", "required": true}]}}, {"id": "node_3", "type": "output", "position": {"x": 502.3528666747269, "y": 370.94234132778445}, "data": {"label": "Flow Output", "description": "Define output variables from this flow", "outputs": [{"name": "result", "type": "string"}]}}]	[{"id": "reactflow__edge-node_2-node_1", "source": "node_2", "target": "node_1", "sourceHandle": null, "targetHandle": null, "label": null}, {"id": "reactflow__edge-node_1-node_3", "source": "node_1", "target": "node_3", "sourceHandle": null, "targetHandle": null, "label": null}]	2	[]	1	2025-10-08 11:35:27.09159	2025-10-08 18:19:05.821157
someflow	A new workflow	DRAFT	[]	[]	1	[]	4	2025-10-08 21:37:47.530922	2025-10-08 21:41:02.1245
New Flow	A new workflow	ARCHIVED	[]	[]	1	[]	2	2025-10-08 14:38:15.718706	2025-10-08 22:36:40.312707
New Flow	A new workflow	ARCHIVED	[]	[]	1	[]	5	2025-10-08 23:00:59.23569	2025-10-08 23:01:07.69091
flow-flow	A new workflow	DRAFT	[{"id": "node_1", "type": "agent", "position": {"x": 304.724748157637, "y": 79.86072048314244}, "data": {"label": "Agent Node", "width": 260, "agent_id": 1}}]	[]	2	[]	3	2025-10-08 18:19:08.722412	2025-10-08 23:56:55.293501
New Flow	A new workflow	ARCHIVED	[]	[]	1	[]	6	2025-10-09 00:00:20.206472	2025-10-09 00:01:42.077232
Research to Article Workflow	A complete workflow that researches a topic and creates a comprehensive article	ACTIVE	[{"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Research Topic", "description": "Enter the topic you want to research", "inputs": [{"name": "topic", "type": "string", "required": true}, {"name": "depth", "type": "string", "required": false, "default": "comprehensive"}], "width": 300}}, {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 300}, "data": {"label": "Research Phase", "agent_id": 3, "agent_name": "Research Analyst", "task": "Conduct comprehensive research on {topic}. Focus on the latest developments, key players, and future trends. Depth: {depth}", "expected_output": "A detailed research report with citations, statistics, and actionable insights", "context": "You are researching for a tech blog that publishes cutting-edge content", "width": 320}}, {"id": "condition-1", "type": "condition", "position": {"x": 100, "y": 500}, "data": {"label": "Quality Gate", "condition": "word_count >= 500 && citations >= 3", "description": "Ensure research meets minimum quality standards", "width": 280}}, {"id": "agent-2", "type": "agent", "position": {"x": 450, "y": 500}, "data": {"label": "Content Writing", "agent_id": 1, "agent_name": "Content Writer", "task": "Using the research provided, write an engaging and informative article about {topic}. Make it accessible yet authoritative.", "expected_output": "A well-structured article (800-1200 words) with introduction, body sections, and conclusion", "context": "You are writing for a tech-savvy audience that values both depth and readability", "width": 320}}, {"id": "output-1", "type": "output", "position": {"x": 450, "y": 700}, "data": {"label": "Final Article", "description": "The completed research article ready for publication", "outputs": [{"name": "article", "type": "string"}, {"name": "word_count", "type": "number"}, {"name": "citations", "type": "array"}, {"name": "metadata", "type": "object"}], "width": 300}}]	[{"id": "edge-1", "source": "input-1", "target": "agent-1", "type": "default"}, {"id": "edge-2", "source": "agent-1", "target": "condition-1", "type": "default"}, {"id": "edge-3", "source": "condition-1", "target": "agent-2", "type": "default"}, {"id": "edge-4", "source": "agent-2", "target": "output-1", "type": "default"}]	1	["research", "content", "example", "default"]	7	2025-10-09 00:07:49.179248	2025-10-09 00:07:49.179249
New Flow	A new workflow	ARCHIVED	[]	[]	1	[]	8	2025-10-09 17:41:22.118471	2025-10-09 17:41:27.447639
testflow	A new workflow	DRAFT	[]	[]	1	[]	9	2025-10-09 21:04:37.901255	2025-10-10 21:09:11.444078
\.


--
-- Data for Name: llm_providers; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.llm_providers (tenant_id, name, provider_type, model_name, api_base, api_key, config, is_active, is_default, id, created_at, updated_at) FROM stdin;
1	OpenAI GPT-4	OPENAI	gpt-4	\N	sk-placeholder-replace-with-real-key	{}	t	f	3	2025-10-09 00:07:49.167586	2025-10-10 10:54:09.500427
1	ollama	OLLAMA	ollama/llama3.1	http://192.168.1.178:11434	Z0FBQUFBQm81Y21MVTdzdlJkSy02ZEVvZHVMTHlLcFF5TVlmZmFlTk91MFpFSWV4X21TdW8xanNCZHVNZmNMdlZlaTBSclhXc2RGUkVHd21RSWI3NjNEV0NuR1o0S1pMdXc9PQ==	{}	t	t	1	2025-10-08 02:15:16.131392	2025-10-11 01:04:15.428161
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.notifications (tenant_id, user_id, type, title, message, data, is_read, read_at, id, created_at, updated_at) FROM stdin;
1	1	info	New reply in 'test-prompts'	It seems like you're referring to an article about "Article Writer" but didn't provide the content. I'm here to help wit…	{"chat_session_id": 11, "kind": "chat_response"}	f	\N	1	2025-10-11 20:38:05.620662	2025-10-11 20:38:05.620663
1	1	info	New reply in 'test-prompts'	It looks like you might be trying to link to a self-referential topic "Article Writer" but didn't provide more context. …	{"chat_session_id": 11, "kind": "chat_response"}	f	\N	2	2025-10-11 20:52:09.152641	2025-10-11 20:52:09.152644
1	1	info	New reply in 'asdas'	**Model Alignment: A Deep Dive into Ensuring AI Systems Reflect Human Values**\n\nIn the realm of artificial intelligence …	{"chat_session_id": 12, "kind": "chat_response"}	f	\N	3	2025-10-11 21:24:44.351839	2025-10-11 21:24:44.351842
1	1	info	New reply in 'asdas'	**Large Language Model (LLM) Training: A Comprehensive Guide**\n\nThe development of Large Language Models (LLMs) has revo…	{"chat_session_id": 12, "kind": "chat_response"}	f	\N	4	2025-10-11 22:04:40.723235	2025-10-11 22:04:40.723238
1	1	info	New reply in 'test-atools'	Hello! It seems like you just said "hello" twice. Is there something I can help you with or would you like to chat?	{"chat_session_id": 13, "kind": "chat_response"}	f	\N	5	2025-10-11 23:36:28.879625	2025-10-11 23:36:28.879627
1	1	info	New reply in 'test-atools'	To evaluate the given mathematical expression `y = 2x + 1` when `x` is 2, I'll use a calculator to perform the calculati…	{"chat_session_id": 13, "kind": "chat_response"}	f	\N	6	2025-10-11 23:37:03.546655	2025-10-11 23:37:03.546662
1	1	info	New reply in 'test-atools'	**Fine-Tuning: The Nuances of Optimizing Complex Systems**\n\nIn the realm of complex systems, optimization is a multiface…	{"chat_session_id": 13, "kind": "chat_response"}	f	\N	7	2025-10-11 23:58:35.730522	2025-10-11 23:58:35.730532
\.


--
-- Data for Name: prompt_categories; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_categories (id, tenant_id, name, description, icon, color, created_at, updated_at) FROM stdin;
9eefd80e-46d0-42ac-944b-e3b870a7cdde	1	Content	Content Writing	\N	\N	2025-10-11 20:33:55.878154	2025-10-11 20:33:55.878158
03971fc8-b597-4c45-9239-62114b0b3254	1	Writing	Writing tasks and content generation	\N	\N	2025-10-11 21:48:29.163382	2025-10-11 21:48:29.163384
00672d26-f625-46e5-a2f4-c549269f0863	1	Research	Structured research and analysis	\N	\N	2025-10-11 21:48:29.165163	2025-10-11 21:48:29.165165
aa765e77-802d-4ebc-9e15-474638b54969	1	Engineering	Code reviews and technical prompts	\N	\N	2025-10-11 21:48:29.166088	2025-10-11 21:48:29.166089
7406049e-a88d-4a78-b46b-403e8d32829e	1	Product	Productivity & operations	\N	\N	2025-10-11 21:48:29.16685	2025-10-11 21:48:29.166851
ed81a8f7-742f-4604-8db6-eabfe1256689	1	Data	Data analysis, planning, and SQL	\N	\N	2025-10-11 21:48:29.167494	2025-10-11 21:48:29.167495
878da19d-8d73-417a-9e39-43d0fa7cc187	1	Marketing	Marketing copy, positioning, and messaging	\N	\N	2025-10-11 21:48:29.167947	2025-10-11 21:48:29.167947
5c892bde-50e4-4e6c-ae96-70ac34924319	1	Support	Customer support and success	\N	\N	2025-10-11 21:48:29.168371	2025-10-11 21:48:29.168372
6fbc4524-8ae9-4f95-9e4a-8cf3db0ede7f	1	Design/UX	UX writing and design prompts	\N	\N	2025-10-11 21:48:29.168763	2025-10-11 21:48:29.168764
\.


--
-- Data for Name: prompt_executions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_executions (id, prompt_id, user_id, tenant_id, context_type, context_id, variables_used, model_used, parameters_used, rendered_content, execution_time_ms, success, error_message, user_satisfaction, created_at) FROM stdin;
\.


--
-- Data for Name: prompt_favorites; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_favorites (id, user_id, prompt_id, created_at) FROM stdin;
\.


--
-- Data for Name: prompt_feedback; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_feedback (id, prompt_id, user_id, feedback_type, content, is_resolved, resolved_by, resolved_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: prompt_ratings; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_ratings (id, prompt_id, user_id, rating, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: prompt_templates; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_templates (id, tenant_id, user_id, category_id, name, slug, description, content, suggested_model, suggested_provider_id, default_temperature, default_top_p, default_top_k, default_max_tokens, default_frequency_penalty, default_presence_penalty, tags, variables, is_public, is_active, is_command_enabled, version, parent_version_id, usage_count, last_used_at, average_rating, total_ratings, total_feedback, created_at, updated_at) FROM stdin;
58b28fdb-78f1-49f4-b1c8-7a9ea6455b86	1	1	9eefd80e-46d0-42ac-944b-e3b870a7cdde	Article Writer	article-writer	Writing detailed articles	You are a talented educational writer with expertise in creating clear, engaging content. You have a gift for explaining complex concepts in accessible language and organizing information in a way that helps readers build their understanding.\n\nAct as Educational Content Writer to help Create engaging, informative content that thoroughly explains {topic} and provides valuable insights to the reader. \n\nKeep the depth of the article {level}\n	ollama/llama3.1	1	0.70	1.00	\N	2000	0.00	0.00	{content,writer,"article generator"}	{"level": {"type": "string", "required": true}, "topic": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 20:34:38.521079	2025-10-11 20:34:38.521081
0c5a9a9d-83b0-427f-aab1-78944419583a	1	1	00672d26-f625-46e5-a2f4-c549269f0863	Research Brief Generator	research-brief	Produce a structured research brief with key findings, sources, and open questions.	Create a concise research brief on: {topic}.\n\nInclude:\n1) Executive summary (4–6 bullet points)\n2) Key insights with short explanations\n3) Notable sources (with 1–2 line annotations)\n4) Open questions / next steps\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{research,analysis}	{"topic": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176342	2025-10-11 21:48:29.176344
f06081ad-9ccc-496f-9357-45a678d9e2ad	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	Email Polisher	email-polisher	Rewrite an email to be clearer, friendlier, and more effective.	Please rewrite the following email to be clear, concise, and kind.\n\nTone guidelines: {tone}.\n\nOriginal email:\n---\n{email}\n---\n\nReturn only the improved email body.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{email,rewrite,tone}	{"tone": {"type": "string", "default": "professional and friendly", "required": false}, "email": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176346	2025-10-11 21:48:29.176347
e0c5fd6b-15f2-49dd-9345-c4925d8ac764	1	1	aa765e77-802d-4ebc-9e15-474638b54969	PR Code Review Checklist	pr-review-checklist	A quick, reusable checklist to apply when reviewing pull requests.	Use this checklist during code review:\n\n- Correctness: logic, edge cases, and error handling\n- Tests: coverage for core paths and tricky cases\n- Readability: naming, structure, comments where needed\n- Security: input validation, secrets, and data handling\n- Performance: obvious hot paths, unnecessary work\n- Consistency: style and patterns used in the repository\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{engineering,review,checklist}	{}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176349	2025-10-11 21:48:29.176349
529d3044-f732-42a4-9a41-0e21d6bc04df	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	Daily Standup Summarizer	standup-summarizer	Summarize daily updates into a crisp standup-style report.	Summarize the following updates into standup format:\n\nYesterday:\n{yesterday}\n\nToday:\n{today}\n\nBlockers:\n{blockers}\n\nReturn a concise, well-formatted summary with bullet points.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{ops,summary,standup}	{"today": {"type": "string", "required": false}, "blockers": {"type": "string", "required": false}, "yesterday": {"type": "string", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.17635	2025-10-11 21:48:29.176351
a996f4c1-9f05-44ea-8530-cf0a3f347638	1	1	ed81a8f7-742f-4604-8db6-eabfe1256689	SQL Query Builder	sql-query-builder	Generate a safe, readable SQL query for a data question based on a schema.	You are a helpful data analyst.\n\nTask: Generate an SQL query to answer the question.\n\nSchema:\n{schema}\n\nQuestion:\n{question}\n\nGuidelines:\n- Use CTEs for clarity when helpful\n- Add brief inline comments for non-trivial steps\n- Avoid vendor-specific features unless required\n- Do not drop or modify tables\n\nReturn only the SQL code block.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{data,sql,analysis}	{"schema": {"type": "string", "required": true, "description": "DDL or table/column descriptions"}, "question": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176352	2025-10-11 21:48:29.176353
74fe53af-e27e-4b0d-8d1e-2ea1033990ea	1	1	aa765e77-802d-4ebc-9e15-474638b54969	Bug Triage	bug-triage	Summarize a bug report and propose severity, impact, and next steps.	Summarize and triage the following bug report.\n\nTitle: {title}\n\nDescription:\n{description}\n\nLogs (optional):\n{logs}\n\nProvide:\n- Summary\n- Severity (Critical/High/Medium/Low)\n- Impact\n- Likely root cause\n- Next steps and owner suggestions\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{engineering,qa,triage}	{"logs": {"type": "string", "required": false}, "title": {"type": "string", "required": true}, "description": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176354	2025-10-11 21:48:29.176355
5b416dcf-eb9c-4b82-b4d0-a6f29f5106c0	1	1	878da19d-8d73-417a-9e39-43d0fa7cc187	Landing Page Hero Copy	landing-page-hero	Craft a compelling hero headline and subheadline for a product landing page.	Create a hero section for a landing page.\n\nProduct: {product_name}\nAudience: {audience}\nPrimary benefit: {benefit}\nTone: {tone}\n\nReturn:\n- Headline (<= 8 words)\n- Subheadline (1–2 short sentences)\n- 3 supporting bullets\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{marketing,copy,landing-page}	{"tone": {"type": "string", "default": "clear, confident, approachable", "required": false}, "benefit": {"type": "string", "required": true}, "audience": {"type": "string", "required": true}, "product_name": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176356	2025-10-11 21:48:29.176357
33e6c6ad-4acf-437d-9135-4d6a830c70ed	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	Meeting Notes Summarizer	meeting-notes-summarizer	Summarize meeting transcript into decisions, action items, and risks.	Summarize the following meeting transcript.\n\nTranscript:\n{transcript}\n\nReturn:\n- Decisions\n- Action items (with owners and due dates if present)\n- Risks / open questions\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{ops,meeting,summary}	{"transcript": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176358	2025-10-11 21:48:29.176358
9d483509-88c1-4209-91c8-ada717c129bc	1	1	aa765e77-802d-4ebc-9e15-474638b54969	Code Explainer	code-explainer	Explain what a code snippet does and identify potential issues.	Explain the following {language} code.\n\nCode:\n---\n{code}\n---\n\nProvide:\n- High-level summary\n- Step-by-step explanation\n- Potential issues (correctness, security, performance)\n- Refactoring suggestions if any\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{engineering,explain,code}	{"code": {"type": "string", "required": true}, "language": {"type": "string", "default": "auto-detect", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.17636	2025-10-11 21:48:29.17636
aa52788c-a5b2-4ef1-9f78-697509c11caf	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	User Story Generator	user-story-generator	Create user stories with persona, goal, and acceptance tests.	Create user stories for the following feature.\n\nFeature: {feature}\nPersona: {persona}\nGoal: {goal}\n\nReturn multiple stories with concise acceptance tests (Gherkin if helpful).	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{product,agile,story}	{"goal": {"type": "string", "required": true}, "feature": {"type": "string", "required": true}, "persona": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176362	2025-10-11 21:48:29.176362
8e6f6d35-9362-445b-803a-9891d1bc0d7f	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	Acceptance Criteria	acceptance-criteria	Draft acceptance criteria from a user story.	Generate acceptance criteria for this user story:\n\n{user_story}\n\nReturn a short, testable checklist.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{product,qa,criteria}	{"user_story": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176364	2025-10-11 21:48:29.176364
7f7c7e24-fa48-462d-bc3a-ab4a4a9f051e	1	1	aa765e77-802d-4ebc-9e15-474638b54969	API Design Outline	api-design-outline	Draft a high-level API design with resources, endpoints, and constraints.	Create an API design outline for the service.\n\nService: {service}\nKnown endpoints (optional): {endpoints}\nConstraints (optional): {constraints}\n\nReturn:\n- Resources & relationships\n- Endpoints with verbs\n- Request/response shapes (concise)\n- Auth and rate limiting\n- Error handling\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{engineering,api,design}	{"service": {"type": "string", "required": true}, "endpoints": {"type": "string", "required": false}, "constraints": {"type": "string", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176365	2025-10-11 21:48:29.176366
cdc1953a-00ab-4a97-868b-dd4e69c9c4a9	1	1	ed81a8f7-742f-4604-8db6-eabfe1256689	Data Analysis Plan	data-analysis-plan	Outline an analysis plan for a data question with methods and pitfalls.	Create an analysis plan for the question.\n\nQuestion: {question}\nData sources (optional): {data_sources}\n\nReturn:\n- Hypotheses & definitions\n- Methods & validation\n- Metrics & visualizations\n- Pitfalls & assumptions\n	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{data,analysis,plan}	{"question": {"type": "string", "required": true}, "data_sources": {"type": "string", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176367	2025-10-11 21:48:29.176367
25906946-957e-4096-b1bf-1c73ca728fb5	1	1	878da19d-8d73-417a-9e39-43d0fa7cc187	Social Post Writer	social-post-writer	Write a concise social post tailored to a platform.	Write a social post about: {topic}.\nPlatform: {platform}.\nTone: {tone}.\n\nReturn 2–3 variants with hashtags where appropriate; keep it concise.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{marketing,social,copy}	{"tone": {"type": "string", "default": "upbeat and informative", "required": false}, "topic": {"type": "string", "required": true}, "platform": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176369	2025-10-11 21:48:29.176369
58187149-4bde-48b3-8d48-bfd087ef00c4	1	1	7406049e-a88d-4a78-b46b-403e8d32829e	Release Notes Generator	release-notes	Turn a list of changes into clear, user-facing release notes.	Create user-facing release notes for version {version}.\n\nChanges:\n{changes}\n\nReturn categorized notes (Improvements, Fixes, Breaking) with a short intro.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{product,release,notes}	{"changes": {"type": "string", "required": true}, "version": {"type": "string", "default": "next", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176371	2025-10-11 21:48:29.176371
b9bac70a-28b5-4175-893e-d07871e4ea3c	1	1	5c892bde-50e4-4e6c-ae96-70ac34924319	Support Reply Composer	support-reply	Draft an empathetic support response with next steps.	Write a support reply.\n\nUser message:\n{user_message}\n\nContext (optional): {context}\nTone: {tone}\n\nReturn a short, empathetic message with clear next steps.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{support,cs,reply}	{"tone": {"type": "string", "default": "empathetic and solution-oriented", "required": false}, "context": {"type": "string", "required": false}, "user_message": {"type": "string", "required": true}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176373	2025-10-11 21:48:29.176373
72687e94-c688-4a1e-abfa-c4d27dcef100	1	1	6fbc4524-8ae9-4f95-9e4a-8cf3db0ede7f	UX Microcopy	ux-microcopy	Generate concise, user-friendly microcopy for UI elements.	Generate UX microcopy.\n\nContext: {context}\nConstraints: {constraints}\nStyle: {style}\n\nReturn 3 options; keep each under 120 characters.	\N	\N	0.70	1.00	\N	\N	0.00	0.00	{design,ux,copy}	{"style": {"type": "string", "default": "concise, friendly, accessible", "required": false}, "context": {"type": "string", "required": true, "description": "Where will this copy appear?"}, "constraints": {"type": "string", "required": false}}	f	t	t	1	\N	0	\N	0.00	0	0	2025-10-11 21:48:29.176376	2025-10-11 21:48:29.176376
\.


--
-- Data for Name: prompt_versions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.prompt_versions (id, prompt_id, version, content, variables, model_params, change_summary, created_by, created_at) FROM stdin;
07aca5c8-2dc7-4e1f-a428-0ddd2adcbef5	58b28fdb-78f1-49f4-b1c8-7a9ea6455b86	1	You are a talented educational writer with expertise in creating clear, engaging content. You have a gift for explaining complex concepts in accessible language and organizing information in a way that helps readers build their understanding.\n\nAct as Educational Content Writer to help Create engaging, informative content that thoroughly explains {topic} and provides valuable insights to the reader. \n\nKeep the depth of the article {level}\n	{"level": {"type": "string", "required": true}, "topic": {"type": "string", "required": true}}	{"top_k": null, "top_p": 1.0, "max_tokens": 2000, "temperature": 0.7, "presence_penalty": 0.0, "frequency_penalty": 0.0}	Initial version	1	2025-10-11 20:34:38.529892
\.


--
-- Data for Name: provider_versions; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.provider_versions (provider_id, version_number, action, changed_by_user_id, configuration, diff_from_previous, change_description, id, created_at, updated_at) FROM stdin;
1	1	CREATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434/", "api_key": null, "config": {}, "is_active": true, "is_default": true}	null	Initial provider creation	1	2025-10-08 02:15:16.140088	2025-10-08 02:15:16.14009
1	2	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": null, "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_base": {"old": "http://192.168.1.178:11434/", "new": "http://192.168.1.178:11434"}}, "removed": {}}	Provider configuration updated	2	2025-10-08 02:15:29.04048	2025-10-08 02:15:29.040482
1	3	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": "Z0FBQUFBQm81Y2xMTWVZWWg1dEJtS1FjN2VfQ2lBY0lMd0taN0ZrT1BORUFZUXI3czBEcGZKb0gwYk9aZ1JMY1M1ek5UUnR0QThkX1I1Q2lDc3hESmdmblFfVEJaVWlTOEE9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_key": {"old": "***encrypted***", "new": "***encrypted***"}}, "removed": {}}	Provider configuration updated	3	2025-10-08 02:15:39.014951	2025-10-08 02:15:39.014952
1	4	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": "Z0FBQUFBQm81Y2xWM1VielpfU3lnS2RYTEdsdkFQTnUyekJvaDFkMHVRY3lwbmRYdFZCdXlvM2dWcFFyX1B1cnZWNVNmNk1CbWx1VXRkbXRZRENwRjNoT09iVkNxWE5GQmc9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_key": {"old": "***encrypted***", "new": "***encrypted***"}}, "removed": {}}	Provider configuration updated	4	2025-10-08 02:15:49.924012	2025-10-08 02:15:49.924014
1	5	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": "Z0FBQUFBQm81Y2xWM1VielpfU3lnS2RYTEdsdkFQTnUyekJvaDFkMHVRY3lwbmRYdFZCdXlvM2dWcFFyX1B1cnZWNVNmNk1CbWx1VXRkbXRZRENwRjNoT09iVkNxWE5GQmc9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {}, "removed": {}}	Provider configuration updated	5	2025-10-08 02:16:00.602342	2025-10-08 02:16:00.602346
1	6	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": "Z0FBQUFBQm81Y21MVTdzdlJkSy02ZEVvZHVMTHlLcFF5TVlmZmFlTk91MFpFSWV4X21TdW8xanNCZHVNZmNMdlZlaTBSclhXc2RGUkVHd21RSWI3NjNEV0NuR1o0S1pMdXc9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_key": {"old": "***encrypted***", "new": "***encrypted***"}}, "removed": {}}	Provider configuration updated	6	2025-10-08 02:16:43.819417	2025-10-08 02:16:43.819421
3	1	UPDATE	\N	{"tenant_id": 1, "name": "OpenAI GPT-4", "provider_type": "openai", "model_name": "gpt-4", "api_base": null, "api_key": "sk-placeholder-replace-with-real-key", "config": {}, "is_active": true, "is_default": false}	null	Provider configuration updated	11	2025-10-10 10:54:09.509885	2025-10-10 10:54:09.509887
1	7	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.35:11434", "api_key": "Z0FBQUFBQm81Y21MVTdzdlJkSy02ZEVvZHVMTHlLcFF5TVlmZmFlTk91MFpFSWV4X21TdW8xanNCZHVNZmNMdlZlaTBSclhXc2RGUkVHd21RSWI3NjNEV0NuR1o0S1pMdXc9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_base": {"old": "http://192.168.1.178:11434", "new": "http://192.168.1.35:11434"}}, "removed": {}}	Provider configuration updated	12	2025-10-10 19:38:28.218609	2025-10-10 19:38:28.218611
1	8	UPDATE	\N	{"tenant_id": 1, "name": "ollama", "provider_type": "ollama", "model_name": "ollama/llama3.1", "api_base": "http://192.168.1.178:11434", "api_key": "Z0FBQUFBQm81Y21MVTdzdlJkSy02ZEVvZHVMTHlLcFF5TVlmZmFlTk91MFpFSWV4X21TdW8xanNCZHVNZmNMdlZlaTBSclhXc2RGUkVHd21RSWI3NjNEV0NuR1o0S1pMdXc9PQ==", "config": {}, "is_active": true, "is_default": true}	{"added": {}, "modified": {"api_base": {"old": "http://192.168.1.35:11434", "new": "http://192.168.1.178:11434"}}, "removed": {}}	Provider configuration updated	13	2025-10-11 01:04:15.440033	2025-10-11 01:04:15.440035
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.tasks (name, description, expected_output, agent_id, crew_id, "order", async_execution, output_format, output_file, context, tools_config, id, created_at, updated_at, variables) FROM stdin;
Analysis Task	Analyze the provided data or research findings.\nIdentify patterns, trends, and insights. Apply critical thinking to draw meaningful conclusions.\nUse analytical tools if available.	A comprehensive analysis report including:\n- Data patterns and trends\n- Key insights and observations\n- Statistical findings (if applicable)\n- Recommendations based on analysis	2	1	1	f	TEXT	\N	\N	\N	2	2025-10-09 17:47:11.079717	2025-10-09 17:47:11.079719	\N
Summarization Task	Summarize the provided content or research findings into a concise format.\nCapture key points and main ideas while maintaining accuracy. Make it accessible\nand easy to understand.	A concise summary that includes:\n- Executive summary (1-2 paragraphs)\n- Key points and takeaways\n- Main conclusions\n- Action items (if applicable)	1	1	2	f	TEXT	\N	\N	\N	3	2025-10-09 17:47:11.081699	2025-10-09 17:47:11.081701	\N
write an article 	write an article about {topic} with level {level} \nThe topic should cover a detailed outline and develop each section and make sure it is consist.\nUse story telling approach for writing the article	an article written in Markdown format with outline at the top and using story telling technique for writing the article sections ensuring consistency	1	4	0	f	TEXT			\N	4	2025-10-10 10:16:05.072014	2025-10-10 21:29:44.831897	["topic", "level"]
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.tenants (name, schema_name, status, api_key, max_users, max_agents, max_flows, settings, id, created_at, updated_at) FROM stdin;
Test	test_de28f32f	ACTIVE	crewai_IaZh6NkI2kCqSUEHy0yzski_2pPDgCjChr_niOIXYgY	10	50	100	{}	1	2025-10-08 02:11:31.622182	2025-10-08 02:11:31.622186
\.


--
-- Data for Name: tools; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.tools (name, description, tool_type, code, docker_image, docker_command, schema, id, created_at, updated_at) FROM stdin;
query	execute static querys.	CUSTOM	def execute(params: dict) -> dict:\n    """\n    Execute the tool with the given parameters.\n\n    Args:\n        params (dict): Input parameters defined by schema\n\n    Returns:\n        dict: Output data matching schema\n    """\n    # Example: Web search tool\n    query = params.get('query', '')\n    max_results = params.get('max_results', 10)\n\n    # Your tool logic here\n    results = perform_search(query, max_results)\n\n    return {\n        'results': results,\n        'count': len(results),\n        'query': query\n    }\n\ndef perform_search(query: str, limit: int) -> list:\n    """Helper function for the tool."""\n    # Implementation here\n    return []\n	\N	\N	{}	1	2025-10-08 09:27:40.353731	2025-10-08 21:39:39.214369
File Reader	Read and analyze file contents	CUSTOM	\ndef read_file(file_path: str) -> str:\n    """Read file contents."""\n    try:\n        with open(file_path, 'r', encoding='utf-8') as f:\n            return f.read()\n    except Exception as e:\n        return f"Error reading file: {str(e)}"\n	\N	\N	{"input": {"file_path": "string"}, "output": {"content": "string"}}	3	2025-10-09 00:07:49.17045	2025-10-09 10:53:51.173126
Calculator	Perform mathematical calculations	CUSTOM	\ndef calculate(expression: str) -> str:\n    """Safely evaluate a mathematical expression."""\n    try:\n        import ast\n        import operator\n\n        # Define safe operations\n        ops = {\n            ast.Add: operator.add,\n            ast.Sub: operator.sub,\n            ast.Mult: operator.mul,\n            ast.Div: operator.truediv,\n            ast.Pow: operator.pow,\n            ast.USub: operator.neg,\n        }\n\n        def eval_expr(node):\n            if isinstance(node, ast.Num):\n                return node.n\n            elif isinstance(node, ast.BinOp):\n                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))\n            elif isinstance(node, ast.UnaryOp):\n                return ops[type(node.op)](eval_expr(node.operand))\n            else:\n                raise TypeError(node)\n\n        result = eval_expr(ast.parse(expression, mode='eval').body)\n        return str(result)\n    except Exception as e:\n        return f"Error calculating: {str(e)}"\n	\N	\N	{"input": {"expression": "string"}, "output": {"result": "number"}}	4	2025-10-09 00:07:49.171011	2025-10-09 10:53:51.173126
Web Search	Search the web using DuckDuckGo - no API key required	CUSTOM	\ndef search_web(query: str, max_results: int = 5) -> str:\n    """Search the web using DuckDuckGo with retry logic.\n\n    Args:\n        query: Search query\n        max_results: Maximum number of results to return (default: 5)\n\n    Returns:\n        Formatted search results as string\n    """\n    import time\n\n    try:\n        from duckduckgo_search import DDGS\n\n        results = []\n        max_retries = 3\n        retry_delay = 2  # seconds\n\n        for attempt in range(max_retries):\n            try:\n                with DDGS() as ddgs:\n                    search_results = list(ddgs.text(query, max_results=max_results))\n\n                    for i, result in enumerate(search_results, 1):\n                        title = result.get('title', 'No title')\n                        body = result.get('body', 'No description')\n                        link = result.get('href', 'No link')\n\n                        results.append(f"{i}. {title}\\n   {body}\\n   URL: {link}\\n")\n\n                    break  # Success - exit retry loop\n\n            except Exception as e:\n                if 'Ratelimit' in str(e) and attempt < max_retries - 1:\n                    # Rate limited - wait and retry\n                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff\n                    continue\n                elif attempt == max_retries - 1:\n                    # Last attempt failed\n                    return f"Search failed after {max_retries} attempts. DuckDuckGo may be rate limiting. Please try again in a few minutes.\\n\\nError: {str(e)}"\n                else:\n                    raise\n\n        if not results:\n            return f"No results found for: {query}"\n\n        return f"Search results for '{query}':\\n\\n" + "\\n".join(results)\n\n    except Exception as e:\n        return f"Error performing web search: {str(e)}\\n\\nNote: If you're seeing rate limit errors, please wait a few minutes before trying again."\n	\N	\N	{"input": {"query": "string (required) - The search query", "max_results": "integer (optional) - Maximum results (default: 5)"}, "output": {"results": "string - Formatted search results"}}	2	2025-10-09 00:07:49.169684	2025-10-09 12:17:08.175861
DuckDuckGo Search	Search the web using DuckDuckGo 	CUSTOM	def search_web(query: str, max_results: int = 5, max_retries: int = 3, retry_delay: int = 2, backoff: float = 2.0, as_dict: bool = False):\n    """Search the web using DuckDuckGo with retry logic.\n\n    Args:\n        query: Search query\n        max_results: Maximum number of results to return (default: 5)\n        max_retries: Number of retry attempts on failure\n        retry_delay: Initial delay before retry (seconds)\n        backoff: Exponential backoff multiplier\n        as_dict: If True, return raw result dicts instead of formatted string\n\n    Returns:\n        Formatted search results as string or list of dicts\n    """\n    import time\n    try:\n        from duckduckgo_search import DDGS\n\n        for attempt in range(max_retries):\n            try:\n                with DDGS() as ddgs:\n                    search_results = list(ddgs.text(query, max_results=max_results))\n\n                if not search_results:\n                    return f"No results found for: {query}"\n\n                if as_dict:\n                    return search_results\n\n                results = []\n                for i, result in enumerate(search_results, 1):\n                    title = result.get('title') or "Untitled"\n                    body = result.get('body') or "No description available"\n                    link = result.get('href') or "No link"\n                    results.append(f"{i}. {title}\\n   {body}\\n   URL: {link}\\n")\n\n                return f"Search results for '{query}':\\n\\n" + "\\n".join(results)\n\n            except Exception as e:\n                if 'Ratelimit' in str(e) and attempt < max_retries - 1:\n                    time.sleep(retry_delay * (backoff ** attempt))\n                    continue\n                elif attempt == max_retries - 1:\n                    return f"Search failed after {max_retries} attempts. Error: {str(e)}"\n                else:\n                    raise\n\n    except Exception as e:\n        return f"Error performing web search: {str(e)}"\n	\N	\N	{}	5	2025-10-10 15:43:12.444147	2025-10-10 15:43:12.444153
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: crewai
--

COPY public.users (tenant_id, email, password_hash, full_name, role, is_active, password_reset_token, password_reset_expires, require_password_change, id, created_at, updated_at) FROM stdin;
1	eng.szaher@gmail.com	$2b$12$sbYMAu.0R.Z9Mn5mDrmF5.sIBFtmdsu65AR/rJBwBIwCqbPNOT0p6	Saad	ADMIN	t	\N	\N	f	1	2025-10-08 02:11:31.854184	2025-10-08 02:11:31.854186
\.


--
-- Name: agent_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.agent_versions_id_seq', 2, true);


--
-- Name: agents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.agents_id_seq', 4, true);


--
-- Name: chat_folders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.chat_folders_id_seq', 1, true);


--
-- Name: chat_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.chat_sessions_id_seq', 13, true);


--
-- Name: crews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.crews_id_seq', 4, true);


--
-- Name: executions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.executions_id_seq', 19, true);


--
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.feedback_id_seq', 1, false);


--
-- Name: flows_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.flows_id_seq', 9, true);


--
-- Name: llm_providers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.llm_providers_id_seq', 3, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.notifications_id_seq', 7, true);


--
-- Name: provider_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.provider_versions_id_seq', 13, true);


--
-- Name: tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.tasks_id_seq', 4, true);


--
-- Name: tenants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.tenants_id_seq', 1, true);


--
-- Name: tools_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.tools_id_seq', 5, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: crewai
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: agent_tools agent_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_tools
    ADD CONSTRAINT agent_tools_pkey PRIMARY KEY (agent_id, tool_id);


--
-- Name: agent_versions agent_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_pkey PRIMARY KEY (id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: chat_folders chat_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_folders
    ADD CONSTRAINT chat_folders_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: crew_agents crew_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crew_agents
    ADD CONSTRAINT crew_agents_pkey PRIMARY KEY (crew_id, agent_id);


--
-- Name: crews crews_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crews
    ADD CONSTRAINT crews_pkey PRIMARY KEY (id);


--
-- Name: executions executions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT executions_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: flows flows_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.flows
    ADD CONSTRAINT flows_pkey PRIMARY KEY (id);


--
-- Name: llm_providers llm_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: prompt_categories prompt_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_categories
    ADD CONSTRAINT prompt_categories_pkey PRIMARY KEY (id);


--
-- Name: prompt_executions prompt_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_executions
    ADD CONSTRAINT prompt_executions_pkey PRIMARY KEY (id);


--
-- Name: prompt_favorites prompt_favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_favorites
    ADD CONSTRAINT prompt_favorites_pkey PRIMARY KEY (id);


--
-- Name: prompt_feedback prompt_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_feedback
    ADD CONSTRAINT prompt_feedback_pkey PRIMARY KEY (id);


--
-- Name: prompt_ratings prompt_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_ratings
    ADD CONSTRAINT prompt_ratings_pkey PRIMARY KEY (id);


--
-- Name: prompt_templates prompt_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_pkey PRIMARY KEY (id);


--
-- Name: prompt_versions prompt_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_pkey PRIMARY KEY (id);


--
-- Name: provider_versions provider_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.provider_versions
    ADD CONSTRAINT provider_versions_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: tools tools_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_agent_versions_agent_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_agent_versions_agent_id ON public.agent_versions USING btree (agent_id);


--
-- Name: ix_agents_llm_provider_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_agents_llm_provider_id ON public.agents USING btree (llm_provider_id);


--
-- Name: ix_chat_folders_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_chat_folders_tenant_id ON public.chat_folders USING btree (tenant_id);


--
-- Name: ix_chat_folders_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_chat_folders_user_id ON public.chat_folders USING btree (user_id);


--
-- Name: ix_chat_sessions_folder_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_chat_sessions_folder_id ON public.chat_sessions USING btree (folder_id);


--
-- Name: ix_chat_sessions_llm_provider_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_chat_sessions_llm_provider_id ON public.chat_sessions USING btree (llm_provider_id);


--
-- Name: ix_chat_sessions_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_chat_sessions_user_id ON public.chat_sessions USING btree (user_id);


--
-- Name: ix_crews_manager_llm_provider_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_crews_manager_llm_provider_id ON public.crews USING btree (manager_llm_provider_id);


--
-- Name: ix_executions_agent_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_agent_id ON public.executions USING btree (agent_id);


--
-- Name: ix_executions_crew_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_crew_id ON public.executions USING btree (crew_id);


--
-- Name: ix_executions_flow_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_flow_id ON public.executions USING btree (flow_id);


--
-- Name: ix_executions_mongo_log_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_mongo_log_id ON public.executions USING btree (mongo_log_id);


--
-- Name: ix_executions_task_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_task_id ON public.executions USING btree (task_id);


--
-- Name: ix_executions_tool_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_tool_id ON public.executions USING btree (tool_id);


--
-- Name: ix_executions_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_executions_user_id ON public.executions USING btree (user_id);


--
-- Name: ix_feedback_agent_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_agent_id ON public.feedback USING btree (agent_id);


--
-- Name: ix_feedback_chat_session_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_chat_session_id ON public.feedback USING btree (chat_session_id);


--
-- Name: ix_feedback_execution_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_execution_id ON public.feedback USING btree (execution_id);


--
-- Name: ix_feedback_feedback_type; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_feedback_type ON public.feedback USING btree (feedback_type);


--
-- Name: ix_feedback_sentiment; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_sentiment ON public.feedback USING btree (sentiment);


--
-- Name: ix_feedback_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_tenant_id ON public.feedback USING btree (tenant_id);


--
-- Name: ix_feedback_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_feedback_user_id ON public.feedback USING btree (user_id);


--
-- Name: ix_llm_providers_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_llm_providers_tenant_id ON public.llm_providers USING btree (tenant_id);


--
-- Name: ix_notifications_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_notifications_tenant_id ON public.notifications USING btree (tenant_id);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_prompt_categories_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_categories_tenant_id ON public.prompt_categories USING btree (tenant_id);


--
-- Name: ix_prompt_executions_prompt_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_executions_prompt_id ON public.prompt_executions USING btree (prompt_id);


--
-- Name: ix_prompt_executions_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_executions_user_id ON public.prompt_executions USING btree (user_id);


--
-- Name: ix_prompt_feedback_prompt_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_feedback_prompt_id ON public.prompt_feedback USING btree (prompt_id);


--
-- Name: ix_prompt_ratings_prompt_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_ratings_prompt_id ON public.prompt_ratings USING btree (prompt_id);


--
-- Name: ix_prompt_templates_category_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_templates_category_id ON public.prompt_templates USING btree (category_id);


--
-- Name: ix_prompt_templates_slug; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_templates_slug ON public.prompt_templates USING btree (slug);


--
-- Name: ix_prompt_templates_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_templates_tenant_id ON public.prompt_templates USING btree (tenant_id);


--
-- Name: ix_prompt_templates_user_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_templates_user_id ON public.prompt_templates USING btree (user_id);


--
-- Name: ix_prompt_versions_prompt_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_prompt_versions_prompt_id ON public.prompt_versions USING btree (prompt_id);


--
-- Name: ix_provider_versions_provider_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_provider_versions_provider_id ON public.provider_versions USING btree (provider_id);


--
-- Name: ix_tasks_agent_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_tasks_agent_id ON public.tasks USING btree (agent_id);


--
-- Name: ix_tasks_crew_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_tasks_crew_id ON public.tasks USING btree (crew_id);


--
-- Name: ix_tenants_api_key; Type: INDEX; Schema: public; Owner: crewai
--

CREATE UNIQUE INDEX ix_tenants_api_key ON public.tenants USING btree (api_key);


--
-- Name: ix_tenants_schema_name; Type: INDEX; Schema: public; Owner: crewai
--

CREATE UNIQUE INDEX ix_tenants_schema_name ON public.tenants USING btree (schema_name);


--
-- Name: ix_tools_name; Type: INDEX; Schema: public; Owner: crewai
--

CREATE UNIQUE INDEX ix_tools_name ON public.tools USING btree (name);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: crewai
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: crewai
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: agent_tools agent_tools_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_tools
    ADD CONSTRAINT agent_tools_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: agent_tools agent_tools_tool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_tools
    ADD CONSTRAINT agent_tools_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES public.tools(id);


--
-- Name: agent_versions agent_versions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_versions agent_versions_changed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_changed_by_user_id_fkey FOREIGN KEY (changed_by_user_id) REFERENCES public.users(id);


--
-- Name: agents agents_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_llm_provider_id_fkey FOREIGN KEY (llm_provider_id) REFERENCES public.llm_providers(id);


--
-- Name: chat_folders chat_folders_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_folders
    ADD CONSTRAINT chat_folders_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: chat_folders chat_folders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_folders
    ADD CONSTRAINT chat_folders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: chat_sessions chat_sessions_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.chat_folders(id);


--
-- Name: chat_sessions chat_sessions_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_llm_provider_id_fkey FOREIGN KEY (llm_provider_id) REFERENCES public.llm_providers(id);


--
-- Name: chat_sessions chat_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: crew_agents crew_agents_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crew_agents
    ADD CONSTRAINT crew_agents_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: crew_agents crew_agents_crew_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crew_agents
    ADD CONSTRAINT crew_agents_crew_id_fkey FOREIGN KEY (crew_id) REFERENCES public.crews(id);


--
-- Name: crews crews_manager_llm_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.crews
    ADD CONSTRAINT crews_manager_llm_provider_id_fkey FOREIGN KEY (manager_llm_provider_id) REFERENCES public.llm_providers(id);


--
-- Name: executions executions_crew_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT executions_crew_id_fkey FOREIGN KEY (crew_id) REFERENCES public.crews(id);


--
-- Name: executions executions_flow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT executions_flow_id_fkey FOREIGN KEY (flow_id) REFERENCES public.flows(id);


--
-- Name: executions executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: feedback feedback_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: feedback feedback_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.executions(id);


--
-- Name: feedback feedback_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: executions fk_executions_agent_id; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT fk_executions_agent_id FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: executions fk_executions_task_id; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT fk_executions_task_id FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: executions fk_executions_tool_id; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.executions
    ADD CONSTRAINT fk_executions_tool_id FOREIGN KEY (tool_id) REFERENCES public.tools(id);


--
-- Name: llm_providers llm_providers_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: notifications notifications_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_categories prompt_categories_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_categories
    ADD CONSTRAINT prompt_categories_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: prompt_executions prompt_executions_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_executions
    ADD CONSTRAINT prompt_executions_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompt_templates(id);


--
-- Name: prompt_executions prompt_executions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_executions
    ADD CONSTRAINT prompt_executions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: prompt_executions prompt_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_executions
    ADD CONSTRAINT prompt_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_favorites prompt_favorites_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_favorites
    ADD CONSTRAINT prompt_favorites_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompt_templates(id);


--
-- Name: prompt_favorites prompt_favorites_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_favorites
    ADD CONSTRAINT prompt_favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_feedback prompt_feedback_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_feedback
    ADD CONSTRAINT prompt_feedback_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompt_templates(id);


--
-- Name: prompt_feedback prompt_feedback_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_feedback
    ADD CONSTRAINT prompt_feedback_resolved_by_fkey FOREIGN KEY (resolved_by) REFERENCES public.users(id);


--
-- Name: prompt_feedback prompt_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_feedback
    ADD CONSTRAINT prompt_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_ratings prompt_ratings_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_ratings
    ADD CONSTRAINT prompt_ratings_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompt_templates(id);


--
-- Name: prompt_ratings prompt_ratings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_ratings
    ADD CONSTRAINT prompt_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_templates prompt_templates_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.prompt_categories(id);


--
-- Name: prompt_templates prompt_templates_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES public.prompt_templates(id);


--
-- Name: prompt_templates prompt_templates_suggested_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_suggested_provider_id_fkey FOREIGN KEY (suggested_provider_id) REFERENCES public.llm_providers(id);


--
-- Name: prompt_templates prompt_templates_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: prompt_templates prompt_templates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: prompt_versions prompt_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: prompt_versions prompt_versions_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.prompt_versions
    ADD CONSTRAINT prompt_versions_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompt_templates(id);


--
-- Name: provider_versions provider_versions_changed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.provider_versions
    ADD CONSTRAINT provider_versions_changed_by_user_id_fkey FOREIGN KEY (changed_by_user_id) REFERENCES public.users(id);


--
-- Name: provider_versions provider_versions_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.provider_versions
    ADD CONSTRAINT provider_versions_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: tasks tasks_crew_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_crew_id_fkey FOREIGN KEY (crew_id) REFERENCES public.crews(id);


--
-- Name: users users_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: crewai
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- PostgreSQL database dump complete
--

\unrestrict jVAb4Nc26owt4Gpu8vMR6cFonxi9TlAOlgeAp8NRIXqKZsanVQ0qvs9fwqzhMAB

