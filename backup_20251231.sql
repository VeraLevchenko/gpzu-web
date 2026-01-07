--
-- PostgreSQL database dump
--

-- Dumped from database version 12.22 (Ubuntu 12.22-0ubuntu0.20.04.4)
-- Dumped by pg_dump version 12.22 (Ubuntu 12.22-0ubuntu0.20.04.4)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: applications; Type: TABLE; Schema: public; Owner: gpzu_user
--

CREATE TABLE public.applications (
    id integer NOT NULL,
    number character varying(50) NOT NULL,
    date character varying(50) NOT NULL,
    applicant character varying(500) NOT NULL,
    phone character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    cadnum character varying(50) NOT NULL,
    address text NOT NULL,
    area double precision,
    permitted_use text,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.applications OWNER TO gpzu_user;

--
-- Name: applications_id_seq; Type: SEQUENCE; Schema: public; Owner: gpzu_user
--

CREATE SEQUENCE public.applications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.applications_id_seq OWNER TO gpzu_user;

--
-- Name: applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpzu_user
--

ALTER SEQUENCE public.applications_id_seq OWNED BY public.applications.id;


--
-- Name: gp; Type: TABLE; Schema: public; Owner: gpzu_user
--

CREATE TABLE public.gp (
    id integer NOT NULL,
    application_id integer NOT NULL,
    out_number integer NOT NULL,
    out_date character varying(10) NOT NULL,
    out_year integer NOT NULL,
    xml_data text,
    attachment character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.gp OWNER TO gpzu_user;

--
-- Name: gp_id_seq; Type: SEQUENCE; Schema: public; Owner: gpzu_user
--

CREATE SEQUENCE public.gp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gp_id_seq OWNER TO gpzu_user;

--
-- Name: gp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpzu_user
--

ALTER SEQUENCE public.gp_id_seq OWNED BY public.gp.id;


--
-- Name: refusals; Type: TABLE; Schema: public; Owner: gpzu_user
--

CREATE TABLE public.refusals (
    id integer NOT NULL,
    application_id integer NOT NULL,
    out_number integer NOT NULL,
    out_date character varying(10) NOT NULL,
    out_year integer NOT NULL,
    reason_code character varying(50) NOT NULL,
    reason_text text,
    attachment character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.refusals OWNER TO gpzu_user;

--
-- Name: refusals_id_seq; Type: SEQUENCE; Schema: public; Owner: gpzu_user
--

CREATE SEQUENCE public.refusals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.refusals_id_seq OWNER TO gpzu_user;

--
-- Name: refusals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpzu_user
--

ALTER SEQUENCE public.refusals_id_seq OWNED BY public.refusals.id;


--
-- Name: tu_requests; Type: TABLE; Schema: public; Owner: gpzu_user
--

CREATE TABLE public.tu_requests (
    id integer NOT NULL,
    application_id integer NOT NULL,
    out_number integer NOT NULL,
    out_date character varying(10) NOT NULL,
    out_year integer NOT NULL,
    rso_type character varying(50) NOT NULL,
    rso_name text,
    attachment character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.tu_requests OWNER TO gpzu_user;

--
-- Name: tu_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: gpzu_user
--

CREATE SEQUENCE public.tu_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tu_requests_id_seq OWNER TO gpzu_user;

--
-- Name: tu_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gpzu_user
--

ALTER SEQUENCE public.tu_requests_id_seq OWNED BY public.tu_requests.id;


--
-- Name: applications id; Type: DEFAULT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.applications ALTER COLUMN id SET DEFAULT nextval('public.applications_id_seq'::regclass);


--
-- Name: gp id; Type: DEFAULT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.gp ALTER COLUMN id SET DEFAULT nextval('public.gp_id_seq'::regclass);


--
-- Name: refusals id; Type: DEFAULT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.refusals ALTER COLUMN id SET DEFAULT nextval('public.refusals_id_seq'::regclass);


--
-- Name: tu_requests id; Type: DEFAULT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.tu_requests ALTER COLUMN id SET DEFAULT nextval('public.tu_requests_id_seq'::regclass);


--
-- Data for Name: applications; Type: TABLE DATA; Schema: public; Owner: gpzu_user
--

COPY public.applications (id, number, date, applicant, phone, email, cadnum, address, area, permitted_use, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: gp; Type: TABLE DATA; Schema: public; Owner: gpzu_user
--

COPY public.gp (id, application_id, out_number, out_date, out_year, xml_data, attachment, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: refusals; Type: TABLE DATA; Schema: public; Owner: gpzu_user
--

COPY public.refusals (id, application_id, out_number, out_date, out_year, reason_code, reason_text, attachment, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tu_requests; Type: TABLE DATA; Schema: public; Owner: gpzu_user
--

COPY public.tu_requests (id, application_id, out_number, out_date, out_year, rso_type, rso_name, attachment, created_at, updated_at) FROM stdin;
\.


--
-- Name: applications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpzu_user
--

SELECT pg_catalog.setval('public.applications_id_seq', 1, false);


--
-- Name: gp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpzu_user
--

SELECT pg_catalog.setval('public.gp_id_seq', 1, false);


--
-- Name: refusals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpzu_user
--

SELECT pg_catalog.setval('public.refusals_id_seq', 1, false);


--
-- Name: tu_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gpzu_user
--

SELECT pg_catalog.setval('public.tu_requests_id_seq', 1, false);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: gp gp_pkey; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.gp
    ADD CONSTRAINT gp_pkey PRIMARY KEY (id);


--
-- Name: refusals refusals_pkey; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.refusals
    ADD CONSTRAINT refusals_pkey PRIMARY KEY (id);


--
-- Name: tu_requests tu_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.tu_requests
    ADD CONSTRAINT tu_requests_pkey PRIMARY KEY (id);


--
-- Name: gp uq_gp_year_number; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.gp
    ADD CONSTRAINT uq_gp_year_number UNIQUE (out_year, out_number);


--
-- Name: refusals uq_refusal_year_number; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.refusals
    ADD CONSTRAINT uq_refusal_year_number UNIQUE (out_year, out_number);


--
-- Name: tu_requests uq_tu_application_rso; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.tu_requests
    ADD CONSTRAINT uq_tu_application_rso UNIQUE (application_id, rso_type);


--
-- Name: tu_requests uq_tu_year_number; Type: CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.tu_requests
    ADD CONSTRAINT uq_tu_year_number UNIQUE (out_year, out_number);


--
-- Name: ix_applications_cadnum; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_applications_cadnum ON public.applications USING btree (cadnum);


--
-- Name: ix_applications_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_applications_id ON public.applications USING btree (id);


--
-- Name: ix_applications_number; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE UNIQUE INDEX ix_applications_number ON public.applications USING btree (number);


--
-- Name: ix_gp_application_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE UNIQUE INDEX ix_gp_application_id ON public.gp USING btree (application_id);


--
-- Name: ix_gp_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_gp_id ON public.gp USING btree (id);


--
-- Name: ix_gp_out_number; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_gp_out_number ON public.gp USING btree (out_number);


--
-- Name: ix_gp_out_year; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_gp_out_year ON public.gp USING btree (out_year);


--
-- Name: ix_refusals_application_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE UNIQUE INDEX ix_refusals_application_id ON public.refusals USING btree (application_id);


--
-- Name: ix_refusals_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_refusals_id ON public.refusals USING btree (id);


--
-- Name: ix_refusals_out_number; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_refusals_out_number ON public.refusals USING btree (out_number);


--
-- Name: ix_refusals_out_year; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_refusals_out_year ON public.refusals USING btree (out_year);


--
-- Name: ix_tu_requests_application_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_tu_requests_application_id ON public.tu_requests USING btree (application_id);


--
-- Name: ix_tu_requests_id; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_tu_requests_id ON public.tu_requests USING btree (id);


--
-- Name: ix_tu_requests_out_number; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_tu_requests_out_number ON public.tu_requests USING btree (out_number);


--
-- Name: ix_tu_requests_out_year; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_tu_requests_out_year ON public.tu_requests USING btree (out_year);


--
-- Name: ix_tu_requests_rso_type; Type: INDEX; Schema: public; Owner: gpzu_user
--

CREATE INDEX ix_tu_requests_rso_type ON public.tu_requests USING btree (rso_type);


--
-- Name: gp gp_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.gp
    ADD CONSTRAINT gp_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: refusals refusals_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.refusals
    ADD CONSTRAINT refusals_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: tu_requests tu_requests_application_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gpzu_user
--

ALTER TABLE ONLY public.tu_requests
    ADD CONSTRAINT tu_requests_application_id_fkey FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

