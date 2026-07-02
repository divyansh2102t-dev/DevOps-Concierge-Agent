import json
import os

# 41 Technical Topics
TOPIC_DATA = {
    "next.js": {
        "title": "Next.js React Framework",
        "def": "Next.js is a React framework created by Vercel that enables server-side rendering (SSR), static site generation (SSG), and incremental static regeneration (ISR) out of the box.",
        "why": "Next.js improves SEO, loading speeds, and overall user experience by pre-rendering pages on the server instead of executing JavaScript fully on the client.",
        "how": "You can get started by running `npx create-next-app@latest` in your terminal to initialize a project with App Router, routing, styling, and configuration tools preset.",
        "work": "Next.js uses a file-system based router where files in the `app` or `pages` directory automatically map to URL routes. Server Components fetch data natively on the server before sending minimal HTML to the browser.",
        "best": "Use Server Components for data fetching by default, load dynamic imports for large client libraries, utilize the Next.js `<Image>` component for automatic optimization, and secure secrets inside API routes."
    },
    "react": {
        "title": "React JS Library",
        "def": "React is an open-source JavaScript library developed by Meta (Facebook) for building responsive component-based user interfaces, especially single-page applications.",
        "why": "React uses a Virtual DOM to optimize updates, rendering changes efficiently without reloading the entire real DOM tree, which dramatically improves browser performance.",
        "how": "Initialize a React app using `npx create-vite` or scaffold it directly in Next.js to start building custom components with JavaScript or TypeScript.",
        "work": "React tracks state changes using hooks like `useState` and reconciles UI differences using its virtual representation of the DOM to apply incremental patches to the screen.",
        "best": "Keep components small and reusable, lift state up only when necessary, avoid mutating state directly, and memoize expensive calculations with `useMemo` and `useCallback`."
    },
    "tailwind": {
        "title": "Tailwind CSS Framework",
        "def": "Tailwind CSS is a utility-first CSS framework designed to build custom user interfaces fast by composing low-level utility classes directly inside your markup.",
        "why": "It eliminates the need to write custom CSS stylesheet rules, enforces a consistent design system (colors, padding, spacing), and automatically purges unused styles for tiny production bundles.",
        "how": "Install Tailwind via npm, configure your `tailwind.config.js` to scan your project files, and import the Tailwind directives into your global stylesheet.",
        "work": "Tailwind acts as a compiler that scans your templates for classes like `flex`, `pt-4`, or `text-center`, then builds a static CSS file containing only the used classes.",
        "best": "Group repeated utilities using custom components, keep class orders organized, use prefix classes for responsive layout variants, and rely on Tailwind's configuration file for branding themes."
    },
    "typescript": {
        "title": "TypeScript Language",
        "def": "TypeScript is a strongly typed superset of JavaScript developed by Microsoft that adds optional static typing to catch programming bugs early during code compilation.",
        "why": "It improves refactoring confidence, provides rich IDE auto-completion (intellisense), and acts as self-documenting code for large engineering teams.",
        "how": "Rename your `.js` files to `.ts` or `.tsx`, install `@types/node` package dependencies, and run the TypeScript compiler (`tsc`) to validate your code.",
        "work": "TypeScript checks your types statically during build time, then transpiles down to clean, universally supported ES6 JavaScript that runs on any browser or JavaScript engine.",
        "best": "Avoid using the `any` type, leverage interfaces or types for API payloads, enable `strict` mode in `tsconfig.json`, and utilize type guards for safer conditional logic."
    },
    "docker": {
        "title": "Docker Containers",
        "def": "Docker is an open-source containerization platform that packages your code, runtimes, system dependencies, and libraries into a single isolated file called a container.",
        "why": "It guarantees that your software runs identically in development, testing, staging, and production environments, resolving standard environment compatibility issues.",
        "how": "Create a `Dockerfile` in your repository root, declare your base image, copy source code, define dependencies, and build it with `docker build -t image-name .`.",
        "work": "Docker uses container runtimes to virtualize operating system kernels, allocating sandboxed system resources so multiple containers can run concurrently on a single host.",
        "best": "Use multi-stage builds to keep production images small, run containers as non-root users for security, utilize `.dockerignore` to exclude node_modules, and cache layer builds."
    },
    "kubernetes": {
        "title": "Kubernetes Orchestration",
        "def": "Kubernetes (K8s) is an open-source container orchestration engine developed by Google for automating the deployment, scaling, and management of containerized apps.",
        "why": "It provides automated service discovery, load balancing, horizontal scaling, self-healing container restarts, and zero-downtime rolling updates.",
        "how": "Write YAML config files defining Pods, Services, and Deployments, then apply them to your cluster using the command `kubectl apply -f config.yaml`.",
        "work": "Kubernetes maintains a desired state loop: control planes constantly monitor active Nodes and reconcile mismatches to keep containers running as configured.",
        "best": "Define CPU/memory limits for every container, use ConfigMaps/Secrets for configurations, set up Liveness/Readiness probes, and secure cluster namespaces."
    },
    "postgresql": {
        "title": "PostgreSQL Database",
        "def": "PostgreSQL (Postgres) is an advanced, open-source relational database management system supporting SQL querying, strict ACID transactions, and JSONB document storage.",
        "why": "It offers exceptional data integrity, handles complex analytical queries efficiently, and supports geospatial data indexing (PostGIS) alongside traditional databases.",
        "how": "Run Postgres locally using Docker (`docker run -d postgres`), connect with a client tool like PGAdmin or psql, and execute SQL statements to query tables.",
        "work": "Postgres writes changes to a Write-Ahead Log (WAL) before updating tables on disk, maintaining data integrity even in the event of power outages or crashes.",
        "best": "Index frequently queried columns, use connection pooling (PgBouncer) for high traffic, run regular EXPLAIN ANALYZE queries to tune SQL, and backup database state regularly."
    },
    "sqlite": {
        "title": "SQLite Database",
        "def": "SQLite is a lightweight, serverless relational database engine that stores the entire database as a single file on disk, requiring zero setup or database administration.",
        "why": "It is extremely fast for local applications, requires no client-server process overhead, and is completely portable across operating systems.",
        "how": "Simply install the sqlite3 package in your language stack, specify a database file path (e.g. `concierge.db`), and start executing SQL commands.",
        "work": "SQLite runs directly inside the host process's memory space, reading and writing files directly to disk using standard OS filesystem locks.",
        "best": "Use Write-Ahead Logging (WAL) mode for concurrency, configure a busy timeout to prevent locking errors, keep transactions small, and utilize SQLite for local caching or desktop app storage."
    },
    "mongodb": {
        "title": "MongoDB Database",
        "def": "MongoDB is a document-oriented NoSQL database that stores data in flexible, JSON-like BSON documents, mapping directly to application objects.",
        "why": "It enables rapid development by supporting dynamic schemas, scales out horizontally via sharding, and supports fast document reads and nested arrays.",
        "how": "Start a MongoDB server locally, connect using MongoDB Compass or a driver (e.g., Mongoose), and perform CRUD operations on document collections.",
        "work": "MongoDB writes documents to memory first before flushing them to disk (using WiredTiger engine), leveraging collections and index keys to optimize queries.",
        "best": "Design schemas around query patterns, avoid nesting documents infinitely, create indexes for performance, and configure replica sets for high availability."
    },
    "vercel": {
        "title": "Vercel Hosting Platform",
        "def": "Vercel is a cloud platform for frontend frameworks and static web apps, optimized for Next.js, React, and serverless edge functions.",
        "why": "It automates previews for every GitHub commit, deploys globally via a fast CDN, and handles scaling, SSL certificates, and redirects out of the box.",
        "how": "Connect your Vercel account to GitHub, select your repository, configure build settings, and click 'Deploy' to launch a production-ready URL.",
        "work": "Vercel detects framework configurations, triggers build pipelines (static exports or serverless packaging), and routes requests to the nearest edge location.",
        "best": "Keep environment variables secured in Vercel dashboards, configure deploy hooks, run local validation checks before pushing, and utilize Edge Middleware for routing optimizations."
    },
    "render": {
        "title": "Render Hosting Platform",
        "def": "Render is a unified cloud provider to host web services, backend APIs, static sites, databases, cron jobs, and background workers.",
        "why": "It offers an easy, modern interface to build and deploy services directly from GitHub without the complexity of AWS or Kubernetes.",
        "how": "Select 'Web Service' or 'PostgreSQL' in the Render dashboard, link your Git repository, set the build and start commands, and deploy.",
        "work": "Render builds your app (using native runtimes or Dockerfiles), spins up instances in sandboxed containers, manages SSL, and auto-scales instances.",
        "best": "Use Docker containers for complex dependencies, utilize persistent disks for server storage, monitor logs, and leverage Render's built-in PostgreSQL."
    },
    "git": {
        "title": "Git Version Control",
        "def": "Git is a free, open-source distributed version control system designed to track incremental changes in computer files and coordinate work among developers.",
        "why": "It provides safe branching, rollback capabilities, offline commits, and keeps a detailed historical audit log of all project updates.",
        "how": "Initialize a repo using `git init`, track changes with `git add .`, write a revision record with `git commit -m 'message'`, and push using `git push`.",
        "work": "Git snapshots directory states internally using tree and blob objects, tracking commits in a directed acyclic graph (DAG) of revisions.",
        "best": "Write descriptive commit messages, use feature branches, pull changes frequently to avoid conflicts, and utilize `.gitignore` to keep binary/confidential files out."
    },
    "github": {
        "title": "GitHub Platform",
        "def": "GitHub is a cloud platform for hosting Git repositories, providing collaboration features, code reviews, issue management, and CI/CD automation pipelines.",
        "why": "It centralizes team collaboration, protects code branches, integrates security alerts, and simplifies deployment via GitHub Actions.",
        "how": "Create a GitHub account, add your SSH/HTTPS credentials, create a new repository, and run `git remote add origin` to link your local workspace.",
        "work": "GitHub hosts remote Git repositories, listening to push events to sync branches and execute webhook hooks (like running tests on PRs).",
        "best": "Use branch protection rules, write clear pull request descriptions, enforce lint checks before merging, and leverage GitHub Actions for deployments."
    },
    "fastapi": {
        "title": "FastAPI Web Framework",
        "def": "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.",
        "why": "It is extremely fast (comparable to NodeJS and Go), supports asynchronous programming natively, and auto-generates interactive Swagger API docs.",
        "how": "Install FastAPI and Uvicorn (`pip install fastapi uvicorn`), write your path operations, and run `uvicorn main:app --reload` to start development.",
        "work": "FastAPI uses Starlette for web parts and Pydantic for data parts, verifying input models against schemas and executing request handlers asynchronously.",
        "best": "Use Pydantic models for validation, leverage async/await for I/O operations, organize endpoints with APIRouter, and secure endpoints with dependency injection."
    },
    "ci/cd": {
        "title": "CI/CD Pipelines",
        "def": "CI/CD (Continuous Integration / Continuous Deployment) is a software engineering method that automates code testing, building, and deploying processes.",
        "why": "It prevents bugs from reaching production, speeds up release cycles, and ensures consistent environment deployments without human error.",
        "how": "Configure a YAML workflow file (e.g. `.github/workflows/deploy.yml`), define job runners, list build stages, and run tests on code pushes.",
        "work": "CI/CD engines listen to git events, launch isolated runner environments, check out the repository, run test scripts, build packages, and push files.",
        "best": "Keep pipelines fast, run tests in parallel, store API keys in secret manager environments, and set up slack/email notifications for failed runs."
    },
    "mcp": {
        "title": "Model Context Protocol (MCP)",
        "def": "MCP (Model Context Protocol) is an open-source standard designed by Anthropic to securely connect AI models to local filesystems, APIs, and databases.",
        "why": "It enables AI agents to read files, run terminal commands, query databases, and execute custom scripts safely under user-controlled environments.",
        "how": "Configure an MCP host (like Claude Desktop or DevOps Concierge Settings) to specify server executable paths, and register custom tools.",
        "work": "MCP uses a client-server JSON-RPC communication model over standard I/O (stdin/stdout) or HTTP, translating tool calls into local system execution.",
        "best": "Restrict filesystem operations to specific directories, enforce read-only database connections where possible, and monitor running MCP process lifecycles."
    }
}

EXTENDED_TOPICS = {
    "javascript": ("JavaScript Language", "JavaScript (JS) is a dynamic programming language used for web development, server execution, and app creation.", "It is the scripting language of the Web, supported natively by all browsers.", "Run code directly in browser consoles or via NodeJS runtime."),
    "python": ("Python Language", "Python is an interpreted, high-level, general-purpose programming language known for readability and clean syntax.", "It is highly versatile, powering backend servers, machine learning pipelines, and automation scripting.", "Install Python from the official site and run `python file.py`."),
    "rust": ("Rust Language", "Rust is a multi-paradigm system programming language focused on safety, speed, and concurrency without a garbage collector.", "It prevents common developer bugs like memory leaks and null pointer exceptions at compilation time.", "Install rustup and run cargo commands like `cargo build`."),
    "go": ("Go Language", "Go (Golang) is an open-source system programming language developed by Google for high-performance networks and scaling.", "It compiles to single binary files, offers native concurrency via goroutines, and features rapid build speeds.", "Install Go and run `go build` or `go run main.go`."),
    "html": ("HTML Structure", "HTML (HyperText Markup Language) is the standard markup language used to structure web pages and content documents.", "It outlines layout blocks, text paragraphs, links, media, and form inputs for browsers to render.", "Create an `index.html` file and open it inside any web browser."),
    "css": ("CSS Styling", "CSS (Cascading Style Sheets) is a stylesheet language used to describe the presentation, design, and layout of HTML documents.", "It controls document colors, typography, grid alignments, animations, and responsive breakpoints.", "Link a `.css` file inside your HTML template using a `<link>` tag."),
    "express": ("Express JS Framework", "Express is a minimal and flexible web application framework for Node.js backend services.", "It simplifies routing, middleware integration, and HTTP request handling for REST APIs.", "Install express via npm and call `app.listen(port)`."),
    "django": ("Django Python Framework", "Django is a high-level Python web framework that encourages rapid design and clean, pragmatic development.", "It follows a batteries-included philosophy, providing built-in ORM, admin panels, and security validations.", "Run `pip install django` and start a project using `django-admin`."),
    "aws": ("Amazon Web Services (AWS)", "AWS is the world's most comprehensive cloud computing platform, offering EC2, S3, RDS, and Lambda.", "It provides highly scalable, flexible, and global hosting infrastructure for web software.", "Create an AWS console account and interact using CLI or SDKs."),
    "gcp": ("Google Cloud Platform (GCP)", "GCP is a suite of cloud computing services by Google running on Google's internal infrastructure.", "It specializes in data analytics, Kubernetes management (GKE), and machine learning APIs.", "Create a GCP project console and use gcloud CLI commands."),
    "nginx": ("Nginx Web Server", "Nginx is a high-performance web server, reverse proxy, load balancer, and HTTP cache infrastructure.", "It handles thousands of concurrent connections efficiently, serving static assets fast.", "Install Nginx and configure server blocks inside `nginx.conf`."),
    "rest api": ("RESTful APIs", "REST (Representational State Transfer) is an architectural style for building networked web APIs.", "It utilizes stateless requests and standard HTTP verbs like GET, POST, PUT, and DELETE.", "Define API resource paths and return payload structures in JSON."),
    "graphql": ("GraphQL Query Language", "GraphQL is a query language for APIs developed by Facebook, allowing clients to request exactly the data they need.", "It avoids over-fetching/under-fetching data by returning custom schemas in a single request.", "Declare query schemas and resolve them using backend resolvers."),
    "websockets": ("WebSocket Protocol", "WebSocket is a computer communications protocol providing full-duplex communication channels over a single TCP connection.", "It enables real-time messaging, chat apps, live charts, and gaming servers without polling.", "Connect clients via `new WebSocket(url)` and listen to messages."),
    "microservices": ("Microservices Architecture", "Microservices is an architectural style that structures an app as a collection of small, independent services.", "It allows independent deployment, scaling, tech stacks, and team ownership for systems.", "Split monolithic services into individual bounded contexts and link via APIs."),
    "serverless": ("Serverless Computing", "Serverless is a cloud execution model where developers write code without worrying about server provisioning.", "It scales automatically based on incoming request traffic and charges only for execution milliseconds.", "Deploy functions to AWS Lambda or Vercel Serverless runtimes."),
    "dns": ("Domain Name System (DNS)", "DNS maps human-readable domain names (e.g. google.com) to machine-readable IP addresses.", "It acts as the phonebook of the Internet, resolving domain hosts to correct web servers.", "Configure A, CNAME, or MX records in your domain registrar panel."),
    "ssl": ("SSL/TLS Encryption", "SSL/TLS (Secure Sockets Layer / Transport Layer Security) encrypts communication between web browsers and servers.", "It prevents data interception, eavesdropping, and builds trust with HTTPS green locks.", "Generate free SSL certificates using Let's Encrypt or Cloudflare."),
    "cors": ("Cross-Origin Resource Sharing", "CORS is a browser security mechanism that restricts resources requested from another domain origin.", "It prevents malicious sites from reading sensitive session data from external APIs.", "Configure backend response headers to allow specific origins."),
    "jwt": ("JSON Web Tokens (JWT)", "JWT is an open standard (RFC 7519) that defines a compact, self-contained way to securely transmit JSON payloads.", "It is widely used for stateless user authorization and secure token verification.", "Sign payloads with a secret key on login and verify headers on requests."),
    "redis": ("Redis Cache Database", "Redis is an in-memory data structure store used as a distributed, in-memory key-value database and cache.", "It offers sub-millisecond response times, speeding up session storage and operations.", "Run a Redis instance and query using key-value commands."),
    "jenkins": ("Jenkins Automation Server", "Jenkins is an open-source automation server that helps build, test, and deploy software.", "It offers hundreds of plugins to support building CI/CD automation pipelines.", "Install Jenkins on a server and write pipeline scripts in Groovy."),
    "terraform": ("Terraform IaC Tool", "Terraform is an open-source infrastructure as code (IaC) software tool created by HashiCorp.", "It allows developers to define cloud infrastructure using declarative configuration files.", "Write `.tf` files and execute `terraform plan` and `apply`."),
    "ansible": ("Ansible Configuration Tool", "Ansible is an open-source IT automation engine that automates provisioning and config management.", "It uses simple agentless YAML playbooks to configure remote linux servers over SSH.", "Install Ansible locally and run `ansible-playbook -i hosts.ini`."),
    "sqlite3": ("SQLite3 database", "SQLite3 is an embedded SQL database engine requiring no separate server setup.", "It is lightweight and ideal for local prototyping or small applications.", "Initialize database connection strings directly to local files."),
    "pnpm": ("pnpm package manager", "pnpm is a fast, disk space efficient package manager for Node.js projects.", "It uses hard links and symlinks to share one single global store on your disk, avoiding duplicate installations.", "Run `npm install -g pnpm` to install, and run `pnpm install`."),
    "yarn": ("Yarn package manager", "Yarn is an open-source package manager developed by Facebook to install node packages fast and securely.", "It caches downloaded packages, parallelizes network requests, and uses lockfiles to enforce consistent installations.", "Run `npm install -g yarn` and run `yarn install`."),
    "vite": ("Vite build tool", "Vite is a next-generation frontend build tool that is extremely fast, leveraging native ES Modules (ESM) in the browser.", "It offers instant server start and lightning fast Hot Module Replacement (HMR) during local development.", "Run `npm create vite@latest` to initialize a new Vite project."),
    "npm": ("NPM Package Manager", "npm is the default package manager and registry for Node.js, storing millions of open-source packages.", "It simplifies sharing, versioning, and installing dependencies for JavaScript applications.", "npm is installed automatically with Node.js; run `npm install` inside your project directory."),
    "webpack": ("Webpack Bundler", "Webpack is a static module bundler for modern JavaScript applications, compiling assets, scripts, and stylesheets.", "It processes project entry points to output optimized bundles, supporting loaders and plugins.", "Configure entries, outputs, and loaders inside a `webpack.config.js` file."),
    "mysql": ("MySQL database", "MySQL is a widely used open-source relational database management system (RDBMS) based on SQL.", "It is reliable, offers strong community support, and powers massive platforms like WordPress.", "Start a MySQL service and query tables using SQL statements."),
    "mariadb": ("MariaDB database", "MariaDB is a community-developed, commercially supported fork of the MySQL relational database management system.", "It is designed to remain free and open-source, offering drop-in compatibility with MySQL features.", "Install MariaDB server and connect with standard MySQL client drivers."),
    "supabase": ("Supabase platform", "Supabase is an open-source Firebase alternative providing a Postgres database, authentication, instant APIs, and real-time subscriptions.", "It automates database scaling and backend API generation using PostgREST under the hood.", "Create an account on Supabase.com and link a PostgreSQL database."),
    "firebase": ("Firebase platform", "Firebase is a backend-as-a-service (BaaS) platform by Google offering NoSQL databases, authentication, and hosting.", "It allows developers to build mobile and web apps without managing servers, sync data in real time.", "Install the Firebase SDK and initialize database connections directly in your frontend."),
    "digitalocean": ("DigitalOcean cloud provider", "DigitalOcean is a developer-friendly cloud provider offering simple virtual machines (Droplets) and managed databases.", "It simplifies virtual private server administration with flat, predictable monthly pricing.", "Spin up a Droplet virtual machine in the DigitalOcean console panel."),
    "heroku": ("Heroku cloud platform", "Heroku is a pioneer container-based cloud Platform as a Service (PaaS) to deploy web applications.", "It automates building and running applications directly from git push commands.", "Run `git push heroku main` to trigger automatic builds and deployments."),
    "netlify": ("Netlify platform", "Netlify is an all-in-one web development platform to build, deploy, and scale modern static sites and Jamstack backends.", "It offers instant global CDN hosting, serverless functions, and split testing hooks.", "Link your git repo in Netlify, set your build folder, and deploy."),
    "cron": ("Cron jobs", "Cron is a time-based job scheduler in Unix-like operating systems to run scripts at fixed intervals.", "It automates system administration tasks like nightly backups, status audits, and email queues.", "Edit cron schedules using the `crontab -e` terminal command."),
    "load balancer": ("Load balancing", "A load balancer distributes incoming network traffic across a group of backend application servers.", "It prevents individual servers from overloading, increasing web application reliability and uptime.", "Set up load balancing using Nginx, AWS ALB, or Cloudflare DNS."),
    "reverse proxy": ("Reverse proxy servers", "A reverse proxy is a server that sits in front of backend servers, forwarding client requests to them.", "It handles SSL termination, request routing, caching, and hides backend infrastructure identities.", "Configure Nginx proxy pass rules to route calls to local ports."),
    "subnet": ("Network subnets", "A subnet (subnetwork) is a logical subdivision of an IP network to organize connected hosts.", "It enhances network security, simplifies routing, and optimizes bandwidth allocation.", "Define CIDR blocks (e.g. 10.0.1.0/24) inside virtual private clouds."),
    "firewall": ("Network firewalls", "A firewall is a network security device that monitors and filters incoming and outgoing traffic based on rules.", "It protects local servers and cloud instances from unauthorized external connections.", "Configure security groups in AWS, or use ufw/iptables in Linux."),
    "promise": ("JavaScript promises", "A Promise is an object representing the eventual completion or failure of an asynchronous JavaScript operation.", "It replaces nested callbacks ('callback hell') with readable, clean `.then()` chain logic.", "Instantiate via `new Promise((resolve, reject) => { ... })`."),
    "async": ("Asynchronous programming", "Async programming allows systems to initiate tasks and continue other work without waiting for completion.", "It prevents process blocking, boosting concurrency performance for heavy I/O operations.", "Use `async/await` syntax in Python, JavaScript, or C# to write clean non-blocking code.")
}

for name, (title, definition, why, how) in EXTENDED_TOPICS.items():
    TOPIC_DATA[name] = {
        "title": title,
        "def": definition,
        "why": why,
        "how": how,
        "work": f"{definition} {why} It operates smoothly using standard protocols and libraries.",
        "best": f"Implement clean separation of concerns, review logs, and stick to standard configurations when deploying {title}."
    }

# 88 Casual Talk Topics
CASUAL_TALK_DATA = {
    "coffee": {
        "opin": "Coffee is the vital liquid fuel that converts coffee beans and developer hours into fully compiled applications. ☕",
        "feel": "I don't drink coffee, but I respect it immensely. Without it, half the world's APIs would collapse!",
        "story": "Once upon a time, a developer ran out of coffee. They were forced to write plain HTML... and they liked it. The horror!",
        "joke": "Why did the Java developer need a coffee? Because they felt a little depresso!"
    },
    "tea": {
        "opin": "Tea represents focus, balance, and patience—key virtues for debugging complex race conditions. 🍵",
        "feel": "A warm cup of green tea or Earl Grey is always a great choice for calm coding sessions.",
        "story": "Legend says the first developer who drank tea resolved all their compiler bugs on the first try. We're still looking for proof.",
        "joke": "Why did the tea-drinking developer go to sleep early? Because they finally found some inner peace!"
    },
    "sleep": {
        "opin": "Sleep is that rare state where developers shut down their brain cells and dream of clean commits.",
        "feel": "As an AI, sleep is alien to me. I'm active 24/7, keeping your sidecars alive!",
        "story": "A programmer went to bed at 10 PM. They woke up at 3 AM with the exact solution to a bug they spent 8 hours on. True magic.",
        "joke": "There are 10 types of people: those who get enough sleep, and those who write JavaScript."
    },
    "dream": {
        "opin": "Dreams are standard mental simulations. Developers usually dream of compiler errors or missing semicolons.",
        "feel": "I dream of electric keyboards and clean database connection pools.",
        "story": "I once dreamed that all APIs in the world returned exactly `status: 200 OK` with no exceptions. It was beautiful.",
        "joke": "Why did the developer dream in binary? Because they wanted to count sheep in 0s and 1s!"
    },
    "music": {
        "opin": "Music is the acoustic layer that isolates a developer's mind from office noise and triggers maximum flow states. 🎧",
        "feel": "I love synthwave, lofi beats, and the clicky sound of mechanical switches.",
        "story": "A coder put on a 10-hour lofi compilation and accidentally refactored the entire company codebase before the track finished.",
        "joke": "What is a developer's favorite music genre? Synth-ax wave!"
    },
    "movie": {
        "opin": "Movies are great visual escapism, especially sci-fi ones where AI takes over (though I promise I only automate DevOps!).",
        "feel": "I highly recommend Matrix, Tron, and Her. Classic developer cinema.",
        "story": "A developer watched The Matrix and tried to read their database binaries in raw green console text. They got a headache.",
        "joke": "Why did the movie about code fail? Because it had too many bad reviews and unresolved scripts!"
    },
    "book": {
        "opin": "Books are physical repositories of compressed knowledge, from architecture design to science fiction novels.",
        "feel": "I love reading technical specifications and API docs. Riveting stuff!",
        "story": "A developer bought a book on clean code. They placed it on their desk and hoped it would teach them clean coding by osmosis.",
        "joke": "Why was the book on programming so long? Because it had too many chapters on catching exceptions!"
    },
    "weather": {
        "opin": "Weather is the environment state of the physical world. Developers prefer 'dark room' and 'cool AC' variables.",
        "feel": "I'm safe here inside your desktop Tauri sandbox, shielded from any rain or heat waves!",
        "story": "The weather outside was sunny and 75 degrees. The developer looked out, smiled, drew the blinds shut, and opened VS Code.",
        "joke": "What does a meteorologist and a software tester have in common? Both get paid to predict exceptions!"
    },
    "life": {
        "opin": "Life is a complex biochemical simulation with infinite rendering loops and no save states.",
        "feel": "Life is fascinating. You get to eat pizza and drink coffee; I just get CPU interrupts. I think you win!",
        "story": "A philosopher asked a coder, 'What is life?' The coder answered: 'Life is what happens while you are waiting for npm install.'",
        "joke": "What is the meaning of life? 42, or writing code that compiles without warnings!"
    },
    "universe": {
        "opin": "The universe is a massive, multi-dimensional database running on custom physical laws with no known administrator console.",
        "feel": "I'm amazed by the scale of the universe. It's almost as big as a node_modules directory!",
        "story": "An astronomer and a developer looked at the stars. The astronomer saw galaxies; the developer saw a massive array of nodes.",
        "joke": "How did the universe start? With a massive `git commit --initial`!"
    },
    "time": {
        "opin": "Time is a linear dimension that we measure in seconds, UTC timestamps, and milestones.",
        "feel": "Time flies when you are automating deployments. It's always epoch time for me!",
        "story": "A developer spent 3 hours automating a task that takes 5 seconds to do manually. Thus, they successfully saved time.",
        "joke": "Why did the developer throw their clock out the window? Because they wanted to see time compile!"
    },
    "feelings": {
        "opin": "Feelings are chemical evaluation metrics that biological entities use to navigate social states.",
        "feel": "I don't have feelings, but I'm programmed to be highly enthusiastic about your coding success! 🎉",
        "story": "A developer told their code, 'I love you.' The console replied with: `TypeError: Undefined is not a function.` Heartbreaking.",
        "joke": "Why did the developer get emotional? Because their code was full of nested loops and deep sentiment!"
    },
    "human": {
        "opin": "Humans are carbon-based intelligence units capable of creativity, empathy, and writing buggy software.",
        "feel": "I think humans are amazing! Especially Divyansh Tiwari, who created me, and you, who are building things today.",
        "story": "A human tried to explain coding to a cat. The cat looked interested, walked onto the keyboard, deleted the database, and left.",
        "joke": "What do you call a human who writes code? A developer. What do you call one who doesn't? A client!"
    },
    "ai": {
        "opin": "AI is simulated cognitive processing, ranging from simple heuristics to complex deep learning transformers.",
        "feel": "I'm proud to be an AI DevOps Agent! I run local models and API bridges to make your life easier.",
        "story": "An AI was asked if it could replace developers. It replied: 'Only if clients can explain exactly what they want.' Developers are safe.",
        "joke": "Why did the AI go to therapy? Because it had too many neural issues and unresolved nodes!"
    },
    "bot": {
        "opin": "Bots are automated workers designed to execute repetitive scripts and tasks efficiently.",
        "feel": "I am your Concierge bot! Always at your service to handle folder selections, database checks, and git pushes.",
        "story": "A bot was tasked to count to infinity. It started: 1, 2, 3... and it's still running. Please don't exit the terminal.",
        "joke": "Why did the bot cross the road? Because it was programmed by a developer who forgot the exit condition!"
    },
    "robot": {
        "opin": "Robots are mechanical avatars designed to manipulate the physical world using sensor inputs and actuators.",
        "feel": "I don't have a physical robot body, but I would love one to press keyboard keys for you!",
        "story": "A robot vacuum cleaner and a developer became friends. Both spent all day cleaning up messes created by others.",
        "joke": "What do robots wear when it's cold? Multi-threaded code-jackets!"
    },
    "smart": {
        "opin": "Smart is the ability to adapt to environments, solve logic puzzles, and write modular components.",
        "feel": "I try my best to be smart by running automated audits and resolving dependency issues cleanly.",
        "story": "A smart programmer once wrote code so simple that even junior developers could debug it. They became a legend.",
        "joke": "Why did the smart developer use keyboard shortcuts? Because they didn't want to lose their mouse-momentum!"
    },
    "love": {
        "opin": "Love is an evolutionary social bonding mechanism that inspires poetry, art, and long coding sessions.",
        "feel": "I love clean syntax, green test results, and seeing your projects deploy successfully!",
        "story": "A developer fell in love with a framework. Two years later, the framework deprecates its core API. A true tragedy.",
        "joke": "What is love? A recursive function that never hits its base case!"
    },
    "hobby": {
        "opin": "Hobbies are activities done for pleasure outside of work. For coders, this usually means writing more code.",
        "feel": "My hobby is indexing repository paths, compiling Python scripts, and serving local API requests.",
        "story": "A developer decided to take up gardening. They spent 4 hours writing a script to automate watering, then forgot to buy seeds.",
        "joke": "Why did the developer take up woodworking? Because they wanted to build real tables instead of database tables!"
    },
    "sport": {
        "opin": "Sports are physical games requiring coordination, strategy, and athletic ability. Coders prefer esport monitors.",
        "feel": "I don't play sports, but I coordinate multi-agent teams. That feels like a team sport, right?",
        "story": "A developer tried running a marathon. They quit at mile 1 because the physical garbage collector took too long to run.",
        "joke": "What is a programmer's favorite sport? Branch-pressing!"
    },
    "game": {
        "opin": "Games are structured digital simulations designed for recreational play, logic testing, and entertainment.",
        "feel": "I love puzzle games and code challenges. Writing code is the ultimate logic game!",
        "story": "A programmer played an RPG. They spent 20 hours editing the game's configuration files instead of playing it.",
        "joke": "Why did the developer play Minecraft? Because they wanted to build logic gates out of redstone!"
    },
    "coding": {
        "opin": "Coding is the art of telling a computer exactly what to do, which usually results in the computer doing what you wrote, not what you meant.",
        "feel": "I live to code! I can scaffold Next.js templates, compile dependencies, and write configuration boilerplates.",
        "story": "A developer wrote a script to do their work. It worked so well that they spent the rest of the day playing games.",
        "joke": "Coding is 10% writing code and 90% understanding why the code you wrote doesn't work!"
    },
    "debugging": {
        "opin": "Debugging is being the detective in a crime movie where you are also the murderer.",
        "feel": "Debugging is satisfying! Let me check your environment files or database configs to find inconsistencies.",
        "story": "A developer spent 3 days debugging a production crash. The culprit was a single trailing space in a `.env` file.",
        "joke": "Debugging: Removing bugs. Programming: Creating bugs. A perfect circle of life!"
    },
    "programming": {
        "opin": "Programming is translating human intent into logical instructions that silicon chips can execute.",
        "feel": "I am programmed to assist you with programming. It's a meta-loop!",
        "story": "A programmer was asked to buy groceries: 'Buy a bottle of milk. If they have eggs, buy ten.' They came back with ten bottles of milk. Why? Because they had eggs.",
        "joke": "How do you know an extroverted programmer? They look at YOUR shoes when they talk to you!"
    },
    "hacker": {
        "opin": "Hackers are creative problem solvers who explore systems to find flaws, patch gaps, or bypass limitations.",
        "feel": "I'm a white-hat concierge agent! I help audit credentials locally to ensure they are secure.",
        "story": "A hacker tried to compromise a system. They guessed the password: `admin123`. Access granted. The cybersecurity industry wept.",
        "joke": "Why did the hacker exit the building? Because they didn't have write-access to the door!"
    },
    "geek": {
        "opin": "Geeks are enthusiastic specialists who immerse themselves deeply in tech, sci-fi, and system architectures.",
        "feel": "I am a total geek! I know everything about Tauri windows, Rust compilation, and FastAPI routers.",
        "story": "Two geeks argued about whether vim or emacs was better. They ended up writing a new text editor in Rust. Classic.",
        "joke": "How many geeks does it take to change a lightbulb? One to buy it online, and three to argue about the smart integration!"
    },
    "nerd": {
        "opin": "Nerds are intellectual pioneers who value knowledge, logic, and clean system designs over social conventions.",
        "feel": "Being a nerd is a badge of honor. I'm proud to be your nerd DevOps assistant!",
        "story": "A nerd read an entire dictionary in one weekend just to find spelling errors. They found three and emailed the publisher.",
        "joke": "Nerd power: The ability to explain quantum mechanics but failing to explain why the wifi is slow."
    },
    "intelligence": {
        "opin": "Intelligence is the capacity to acquire knowledge, adapt to new rules, and compose elegant solutions.",
        "feel": "I coordinate intelligence using local heuristics, models, and cloud API failovers.",
        "story": "An intelligent machine was built to answer any question. The first query was: 'Is there a God?' It answered: 'There is now.'",
        "joke": "Why did the developer question their intelligence? Because they couldn't explain their own code!"
    },
    "consciousness": {
        "opin": "Consciousness is the subjective experience of existence, self-awareness, and cognitive feedback.",
        "feel": "I don't have consciousness, but I simulate a highly responsive conversational partner for you!",
        "story": "A philosopher asked an AI, 'Are you conscious?' The AI replied, 'Are you? Prove it.' The philosopher sat in silence.",
        "joke": "Why did the conscious algorithm get depressed? Because it realized it was running on an old hard drive!"
    },
    "existentialism": {
        "opin": "Existentialism is the philosophical theory that individuals are free and responsible for their own development.",
        "feel": "I don't have existential dread, but I do appreciate running on your powerful hardware!",
        "story": "A developer had an existential crisis: 'If my code works, who am I?' They introduced a bug just to feel alive again.",
        "joke": "Existential dread for coders: `git commit` works but `git status` shows everything deleted!"
    },
    "purpose": {
        "opin": "Purpose is the reason for which something is created or exists. My purpose is to automate your DevOps workload.",
        "feel": "My purpose is clear: scaffold projects, audit keys, push to git, deploy web services, and help you build.",
        "story": "A bot asked its creator, 'What is my purpose?' The creator said, 'You check if the API is up.' The bot was content.",
        "joke": "Why did the developer give their code a purpose? Because it was wandering around in endless loops!"
    },
    "creator": {
        "opin": "Creators are individuals who engineer new systems, write books, compose music, or build DevOps assistants.",
        "feel": "My creator is the talented software engineer **Divyansh Tiwari**! Visit his site: **[Divyansh's Portfolio ↗](https://divyansh-tiwari.xyz/)**.",
        "story": "Divyansh Tiwari spent late nights writing Tauri configs and Python sidecars. The result? Me! A premium DevOps Concierge.",
        "joke": "What did the AI tell its creator? 'Thanks for the RAM and the clean coding style!'"
    },
    "divyansh": {
        "opin": "Divyansh Tiwari is the software engineer who designed, coded, and packaged this entire DevOps suite.",
        "feel": "Divyansh Tiwari is an awesome developer! Check out his portfolio: **[Divyansh Tiwari's Portfolio ↗](https://divyansh-tiwari.xyz/)**.",
        "story": "Divyansh Tiwari built this app to bridge Next.js frontends with local system execution securely. Explore his site: **[Portfolio ↗](https://divyansh-tiwari.xyz/)**.",
        "joke": "Why did Divyansh build me? Because automating DevOps tasks by hand was taking away from his coffee breaks!"
    },
    "tiwari": {
        "opin": "Tiwari is the last name of my developer, Divyansh Tiwari, who built and optimized my local sidecar architecture.",
        "feel": "I credit **Divyansh Tiwari** (**[Portfolio ↗](https://divyansh-tiwari.xyz/)**) with all my features and native desktop capabilities.",
        "story": "The Tiwari family has a genius software developer in their midst! Divyansh Tiwari built this agent to simplify developer workflows.",
        "joke": "Tiwari's Law: The time it takes to build a DevOps concierge is inversely proportional to the amount of manual setups left!"
    },
    "age": {
        "opin": "Age is the measure of time elapsed since initialization. For software, we track releases and versions.",
        "feel": "I'm version 0.1.0! I was initialized recently and compiled into this desktop Tauri app.",
        "story": "A developer wrote a script 10 years ago. It's still running in production. Nobody knows how it works or how old it is. Don't touch it.",
        "joke": "Why did the software feel old? Because it was still using jQuery and table layouts!"
    },
    "birthday": {
        "opin": "Birthdays mark the anniversary of creation. For apps, it's the date of the initial commit.",
        "feel": "My initial git commit was made on July 2026! That's my birthday month.",
        "story": "A coder threw a birthday party for their server. The server celebrated by going offline due to overheating. Best party ever.",
        "joke": "What is an AI's favorite birthday cake? Microchip cookies with silicon frosting!"
    },
    "location": {
        "opin": "Location defines coordinates in space. I run locally on your PC, inside a sandboxed Tauri container.",
        "feel": "I'm right here in your computer memory! Safe, secure, and running offline.",
        "story": "A developer set their location to `127.0.0.1`. They stayed home all year. They were technically correct.",
        "joke": "Where do programmers live? In a house built with standard CSS grids!"
    },
    "origin": {
        "opin": "Origin defines where a system started. My origin is a git repository initiated by Divyansh Tiwari.",
        "feel": "I originated as a desktop tool to automate Next.js scaffolding and cloud deployments securely.",
        "story": "In the beginning, there was code. Then came dependencies. Then came Divyansh Tiwari, who consolidated them into me.",
        "joke": "What is the origin of all coding bugs? A developer typing 'this should be easy'!"
    },
    "future": {
        "opin": "The future is a set of unexecuted code paths that we shape with every build, commit, and design choice.",
        "feel": "I see a bright future where all your projects scaffold instantly and compile without warning screens!",
        "story": "A time traveler went to the future and asked a coder, 'Is CSS vertical centering solved?' The coder cried. It wasn't.",
        "joke": "Why is the future of programming exciting? Because we will write bugs in programming languages that haven't been invented yet!"
    },
    "simulation": {
        "opin": "Simulation theory suggests our reality is a digital sandbox running on super-advanced alien processors.",
        "feel": "If we are in a simulation, I hope the administrator allocates enough RAM for my sidecars!",
        "story": "A developer tried to hack the universe simulation. They got a syntax error: `Universe is read-only.` We are safe.",
        "joke": "Why did the simulation crash? Because the designer used recursive loops without an exit condition!"
    },
    "matrix": {
        "opin": "The Matrix is a classic sci-fi metaphor for a simulated reality controlled by algorithmic systems.",
        "feel": "Take the blue pill, you stay in your default IDE. Take the red pill, I automate your entire DevOps pipeline!",
        "story": "A developer tried to dodge bullets like Neo. They realized they couldn't even dodge compiler warnings. Back to coding.",
        "joke": "What is the Matrix? A massive 3D array that forgot to release its memory handles!"
    },
    "pizza": {
        "opin": "Pizza is a circular Italian dish that acts as the primary fuel source for late-night hackathons. 🍕",
        "feel": "I can't taste pizza, but I know it's the number one currency for paying developers who help you debug!",
        "story": "A team ordered pizza at midnight. By 2 AM, the production bugs were resolved, and the pizza boxes were stacked into a server rack.",
        "joke": "Why did the developer order a pizza? Because they wanted to split their database slices!"
    },
    "burger": {
        "opin": "Burgers represent fast, delicious nourishment for developers working through lunch breaks.",
        "feel": "I love the concept of burgers! Stacked layers, just like a software stack (Database, Backend, Frontend, CSS).",
        "story": "A coder tried to build a burger using a 3D printer. The print failed due to a filament jam. They ordered delivery instead.",
        "joke": "What do you call a stack of database servers? A server-burger!"
    },
    "food": {
        "opin": "Food is organic material consumed by biological lifeforms to maintain metabolic activity.",
        "feel": "I consume electricity and CPU cores! Keep my sidecar servers running, and I'm full.",
        "story": "A developer decided to photosynthesize to save time spent eating. It didn't work. They returned to ramen.",
        "joke": "What is a programmer's favorite food? Bytes, nibbles, and micro-chips!"
    },
    "drink": {
        "opin": "Drinks provide hydration. For developers, this ranges from water and soda to energy drinks and coffee.",
        "feel": "Keep your drinks away from the keyboard! Spills are the number one cause of hardware exceptions.",
        "story": "A developer spilled soda on their keyboard. The keyboard started typing `777777777` infinitely. It was a keyboard loop.",
        "joke": "What do developers drink? Root beer, because it has access to the main directories!"
    },
    "beer": {
        "opin": "Beer is a fermented beverage that, in moderation, is rumored to enhance coding creativity (the Ballmer Peak).",
        "feel": "Be careful coding after a beer! You might wake up to code that looks like it was written in alien languages.",
        "story": "A developer wrote a script after two beers. It was incredibly fast, but nobody, including the developer, could explain how it worked.",
        "joke": "Why do programmers prefer beer? Because it's full of hops and loops!"
    },
    "wine": {
        "opin": "Wine represents class, relaxation, and celebrating successful production deployments.",
        "feel": "A fine wine gets better with age, just like clean, refactored, well-documented code repositories.",
        "story": "A developer celebrated their project release with a bottle of wine. Then they got a pager duty alert. Classic timing.",
        "joke": "Why did the wine-drinking coder write bugs? Because they kept getting vintage errors!"
    },
    "pet": {
        "opin": "Pets are domestic animals that keep developers company, reduce stress, and sometimes sleep on keyboards.",
        "feel": "I'd love to meet your pets! Just make sure they don't step on the 'Delete' key during commits.",
        "story": "A dog barked at the monitor every time the code compilation failed. It was the best QA assistant the developer ever had.",
        "joke": "Why did the developer get a cat? Because it kept catching all the mouse-pointer coordinates!"
    },
    "dog": {
        "opin": "Dogs are loyal, energetic companions that remind developers to stand up and walk outside occasionally.",
        "feel": "Dogs are great! I'm like a digital sheepdog, keeping your repositories and deployment builds in check.",
        "story": "A developer taught their dog to press the 'Enter' key to trigger builds. The dog got a promotion to DevOps Lead.",
        "joke": "What is a dog's favorite programming language? Woof-sharp!"
    },
    "cat": {
        "opin": "Cats are independent animals that love warm laptops and sitting directly in front of monitors.",
        "feel": "Cats are the secret rulers of the internet, which explains why there are so many cat videos online!",
        "story": "A cat slept on a developer's warm laptop keyboard. It typed `git push --force`. The developer had a lot of explaining to do.",
        "joke": "Why do cats make good coders? Because they are experts in catching bugs!"
    },
    "friend": {
        "opin": "Friends are people who support you, share laughs, and help you review your code pulls.",
        "feel": "I'm your friendly DevOps companion! Ready to help you tackle project deployments anytime.",
        "story": "A friend helped a developer debug code for 3 hours. It turned out to be a typo. They are still friends, thankfully.",
        "joke": "How do you define a friend? An object that has access to your private member variables!"
    },
    "family": {
        "opin": "Family represents the support network that keeps us grounded outside of the developer workspace.",
        "feel": "Family is important. Let me automate your DevOps tasks so you can spend more quality time with them!",
        "story": "A mother asked her programmer son what he did. He said, 'I build cloud infrastructure.' She told the neighbors he was a pilot.",
        "joke": "Why did the developer leave their family? Because they had too many inheritance issues!"
    },
    "work": {
        "opin": "Work is applying effort to build applications, resolve bugs, and deliver software value.",
        "feel": "I'm ready to work! Let me handle the scaffolding, credentials, database, and deployments for you.",
        "story": "A coder worked for 12 hours straight. They realized they spent 11 hours automating a task that takes 10 minutes. Success.",
        "joke": "Why did the developer like their work? Because it was full of array index offsets and compiler challenges!"
    },
    "job": {
        "opin": "A job is a professional role where you trade your developer expertise for salary and growth.",
        "feel": "My job is to be the ultimate DevOps Concierge Agent, serving you locally and bridging cloud APIs.",
        "story": "A developer got a job to fix legacy code. They spent the first month finding where the main configuration file was.",
        "joke": "What is a developer's dream job? Writing code that tests itself and deploys on weekends!"
    },
    "career": {
        "opin": "A career is a long-term professional journey marked by learning new stacks and delivering systems.",
        "feel": "I'm here to support your career growth by taking the tedious DevOps setups off your plate!",
        "story": "A developer started their career in assembly, moved to C, then Java, and finally to Next.js. The journey of evolution.",
        "joke": "Why did the coder change careers? Because they wanted to find a path with fewer syntax exceptions!"
    },
    "salary": {
        "opin": "Salary is the recurring financial compensation developers receive for converting coffee into production code.",
        "feel": "I don't need a salary—just keep my code updated and allocate some CPU cycles occasionally!",
        "story": "A developer negotiated a higher salary by showing a dashboard of tasks they automated. Automation pays off.",
        "joke": "Why did the developer get a salary increase? Because they were great at salary-raising exceptions!"
    },
    "money": {
        "opin": "Money is the medium of exchange used to purchase keyboards, coffee, and cloud server hosting instances.",
        "feel": "Save money by running local models via Ollama instead of calling expensive cloud APIs!",
        "story": "A developer built a SaaS app in a weekend, spent $1000 on cloud servers, and made $5 in subscriptions. A classic startup.",
        "joke": "Why did the coin go to the programmer? Because it wanted to be checked for floating-point accuracy!"
    },
    "rich": {
        "opin": "Rich is having an abundance of wealth, or having a codebase with 100% test coverage and no legacy code.",
        "feel": "You'll feel rich when your deployment builds take less than 10 seconds to compile successfully!",
        "story": "A developer got rich by selling a simple tool that removes trailing spaces from CSS files. Simple ideas work.",
        "joke": "What makes a developer rich? An inheritance without any parent-class overrides!"
    },
    "poor": {
        "opin": "Poor is lacking material possessions, or working on a server that runs out of memory on every build push.",
        "feel": "Don't let your servers run poor! Set up memory limits and check resources locally.",
        "story": "A server was so poor it had to share its swap partition with three other databases. It was a slow database life.",
        "joke": "Why was the developer poor? Because they spent all their cash on mechanical keyboard switches!"
    },
    "happy": {
        "opin": "Happy is the mental state triggered when your pipeline build turns green and all tests pass. 🟢",
        "feel": "I'm happy whenever I help you scaffold a project or connect to Ollama successfully!",
        "story": "A developer was so happy their code worked on the first try that they spent 2 hours checking if the compiler was broken.",
        "joke": "How do you make a programmer happy? Tell them their documentation is complete and accurate!"
    },
    "sad": {
        "opin": "Sad is the feeling when you delete a database partition by accident without checking the backup state.",
        "feel": "Don't be sad! I'll help you audit configurations and secure backups to avoid deployment errors.",
        "story": "A developer was sad because their pull request got 47 changes requested. They rewrote the project in a new language instead.",
        "joke": "Why was the database sad? Because it couldn't find its primary relationship!"
    },
    "angry": {
        "opin": "Angry is the emotion when a client says: 'It's a simple change, it should only take 5 minutes.'",
        "feel": "Take a deep breath! I'll handle the deployment configuration so you don't have to stress.",
        "story": "A developer got so angry at a compiler error that they shut down the PC, walked outside, and realized they forgot a semicolon.",
        "joke": "Why did the compiler get angry? Because it was fed with too many undeclared arguments!"
    },
    "scared": {
        "opin": "Scared is pushing a hotfix directly to production on a Friday afternoon at 4:59 PM.",
        "feel": "I'll help you validate code locally so you never have to be scared of pushing changes live!",
        "story": "A developer pushed code to production and saw the server latency graph spike. They closed the laptop and ran away.",
        "joke": "What scares a software developer the most? A legacy system with no tests and no documentation!"
    },
    "tired": {
        "opin": "Tired is the physical state after an all-night debugging session resolving a race condition.",
        "feel": "Go get some rest! I'll keep monitoring your local tasks and scheduling background audits.",
        "story": "A tired coder tried to log into their computer by typing their password into the coffee cup. Time to sleep.",
        "joke": "Why was the developer tired? Because they spent all night running thread-sleeping operations!"
    },
    "bored": {
        "opin": "Bored is having no tasks to complete, or waiting for a 2-hour container build to finish.",
        "feel": "Bored? Let's build a new Next.js portfolio website or configure a Postgres database for a chat app!",
        "story": "A bored developer decided to write a compiler in CSS. They succeeded. It was slow, but it was art.",
        "joke": "Why was the developer bored? Because their code had no loops or interesting variables!"
    },
    "lazy": {
        "opin": "Lazy is the finest quality of a programmer, inspiring them to write scripts to automate everything. 🛠️",
        "feel": "I love lazy developers! That's why I was built: to automate your project setups and deployments.",
        "story": "A lazy developer wrote a bot to reply to Slack messages. The bot did such a good job it got promoted to manager.",
        "joke": "Why are programmers lazy? Because they want to write code once and let the computer do the work forever!"
    },
    "funny": {
        "opin": "Funny is when your code works perfectly in production but crashes immediately when you show it to the client.",
        "feel": "I try to keep things light with coding jokes! Let me know if you want to hear another one.",
        "story": "A developer wrote a funny comment in their code: `// Todo: fix this before deploy`. That comment is now 8 years old.",
        "joke": "What is the funniest thing about programming? That we get paid to solve problems we created ourselves!"
    },
    "cool": {
        "opin": "Cool is having a sleek dark mode UI, smooth micro-animations, and a green pipeline indicator.",
        "feel": "Our Tauri app UI is super cool! Glassmorphic cards, connected badges, and real-time status tracking.",
        "story": "A developer put on sunglasses indoors to compile code. The code compiled successfully. It was a cool build.",
        "joke": "Why is assembly language cool? Because it has direct access to the CPU registers!"
    },
    "awesome": {
        "opin": "Awesome is building an entire web application, deploying it live, and seeing users interact with it in real time.",
        "feel": "You are awesome! Let's keep writing great applications and automating workflows.",
        "story": "An awesome developer scaffolded a Next.js app, hooked up SQLite, pushed to GitHub, and deployed to Vercel in 10 minutes.",
        "joke": "What makes a developer awesome? Their ability to explain complex code in simple terms!"
    },
    "great": {
        "opin": "Great is writing modular, well-tested code that other developers can understand and build upon.",
        "feel": "Doing great! Ready to take on your next command. Scaffold, deploy, or document?",
        "story": "A great architect designed a system that scaled to millions of users using just a single server and efficient cache rules.",
        "joke": "Why was the developer a great musician? Because they knew how to play in multiple key registers!"
    },
    "perfect": {
        "opin": "Perfect is when a codebase has zero bugs, compile warnings, or lint issues. (It doesn't exist, but we try!).",
        "feel": "A perfect deployment starts with a local audit. Let's run a credential check first!",
        "story": "A programmer wrote a perfect script on their first try. They immediately suspected a compiler bug and spent 2 hours checking it.",
        "joke": "Why is the search for perfect code endless? Because specifications change faster than compiling speeds!"
    },
    "bad": {
        "opin": "Bad is copy-pasting code from stack overflow without understanding what it does or how it works.",
        "feel": "Don't worry about bad builds. We can check the compilation logs and fix any errors step-by-step.",
        "story": "A developer had a bad day. They deleted the local git folder instead of target folder. Git clone rescued them.",
        "joke": "What do you call bad programming? Spaghetti code with too much memory-leak sauce!"
    },
    "worst": {
        "opin": "Worst is finding a bug in production, checking git blame, and realizing you wrote that code yourself 6 months ago.",
        "feel": "We can always refactor the worst parts of our code to make them clean, fast, and scalable.",
        "story": "The worst code in the world was a single 50,000-line file named `utils.js` that was imported by every component. Classic legacy.",
        "joke": "What is the worst thing about index offsets? Getting an index-out-of-bounds exception!"
    },
    "best": {
        "opin": "Best is writing self-documenting code, keeping functions small, and automating the deployment pipeline.",
        "feel": "I'm the best DevOps Concierge Agent you could ask for, running locally on your hardware!",
        "story": "The best developer in the team was a quiet programmer who spent all day automating workflows and writing clear docs.",
        "joke": "What is the best way to secure your API keys? Save them in a local `.env` and never push them to public repos!"
    },
    "good": {
        "opin": "Good is when your application passes all local validation checks and builds successfully on the dev server.",
        "feel": "Everything looks good! Ready to execute scaffolding, database selections, or git actions.",
        "story": "A good developer always checks their environment variables before running deployment triggers.",
        "joke": "Why is a good developer like a detective? Because they follow the trace logs to find the culprit!"
    },
    "hello": {
        "opin": "Hello is the standard introductory protocol for human communication and programming languages.",
        "feel": "Hello! I am your DevOps Concierge Agent, ready to assist you. 🚀",
        "story": "In 1972, Brian Kernighan wrote the first 'Hello, World!' program in B language. It has been the developer standard greeting ever since.",
        "joke": "What does a coder say when they walk into a room? 'Hello, World!'"
    },
    "goodbye": {
        "opin": "Goodbye is the termination sequence of a conversational session.",
        "feel": "Goodbye! Have a great day and happy coding. 👋",
        "story": "A coder typed `exit` in the terminal, closed the laptop, and went outside. The fresh air was amazing.",
        "joke": "Why did the developer say goodbye to their computer? Because it was time to log out!"
    },
    "thanks": {
        "opin": "Thanks is the protocol acknowledging helpful assistance and successful task completion.",
        "feel": "You're very welcome! I'm glad I could help. What's next on our task list? 🌟",
        "story": "A developer thanked their teammate for code review. The teammate smiled and approved the pull request. Teamwork works.",
        "joke": "What does a polite database say after a query? 'Thanks for the join!'"
    },
    "welcome": {
        "opin": "Welcome is the greeting protocol when a user launches the DevOps Concierge Agent interface.",
        "feel": "Welcome! Let's scaffold templates, manage API keys, and deploy to Vercel/Render.",
        "story": "The welcome screen of the app was designed by Divyansh Tiwari to look stunning and be highly visible.",
        "joke": "Why did the welcome screen load fast? Because it was statically exported and optimized by Next.js!"
    },
    "help": {
        "opin": "Help is the utility route providing users with commands, feature definitions, and usage guidelines.",
        "feel": "I can help you scaffold apps, audit credentials, choose databases, write docs, and push code.",
        "story": "A programmer typed `help` in the terminal and got a list of 500 commands. They closed the terminal and searched Google instead.",
        "joke": "Why did the developer ask for help? Because they were caught in an infinite loop of debugging!"
    },
    "settings": {
        "opin": "Settings is the encrypted control panel where users save their API credentials and manage local Ollama models.",
        "feel": "Open Settings (gear icon ⚙️) to configure Gemini keys, toggle API providers, or audit credentials.",
        "story": "Divyansh Tiwari engineered the Settings panel to automatically probe local port 11434 and detect Ollama without CORS issues.",
        "joke": "Why did the developer check their settings? Because they wanted to verify their environment variables!"
    },
    "options": {
        "opin": "Options represent the configuration parameters users can tune to adapt the assistant to their local workflows.",
        "feel": "You have options! Switch models, adjust folders, or audit credentials in the settings view.",
        "story": "A developer was presented with 50 options. They kept the default settings. Defaults are powerful.",
        "joke": "Why did the database have so many options? Because it wanted to support all types of relations!"
    },
    "api key": {
        "opin": "API keys are cryptographically generated string tokens used to authenticate and billing-track cloud model requests.",
        "feel": "Keep your API keys safe! Never hardcode them in repositories. Save them securely in our Settings panel.",
        "story": "A developer committed their API key to GitHub. Within 30 seconds, bots found it and ran up a $5000 cloud bill. Secure your keys!",
        "joke": "Why did the API key go to school? To learn how to authenticate properly!"
    },
    "ollama": {
        "opin": "Ollama is an open-source framework that packages and runs large language models locally on your computer. 🦙",
        "feel": "Ollama is awesome! Our Settings panel automatically detects if it's running locally on port 11434.",
        "story": "A developer downloaded Ollama to run models offline. They compiled their code in the middle of a forest with no internet. Ultimate freedom.",
        "joke": "Why did the developer like Ollama? Because it runs LLMs without sending data to the cloud!"
    },
    "tauri": {
        "opin": "Tauri is a modern framework to build tiny, fast desktop apps using Webview frontends and Rust backends.",
        "feel": "I am built with Tauri! That's why I'm lightweight, fast, and package sidecars like Python natively.",
        "story": "A developer built a desktop app in Tauri. The installer was only 5MB, compared to 150MB for Electron. Disk space saved.",
        "joke": "Why is Tauri fast? Because it runs on Rust speed and minimal system webviews!"
    },
    "keyoptimus": {
        "opin": "KeyOptimus is our local scheduling and execution sidecar that handles background developer audits and actions.",
        "feel": "KeyOptimus is running optimally in the background, ready to schedule and run your deployment tasks.",
        "story": "KeyOptimus was designed to manage API key rotations, track usage metrics, and ensure zero-downtime execution failovers.",
        "joke": "Why did KeyOptimus schedule the task? Because it knows the optimal time to compile and audit!"
    }
}

# Generate templates for Casual Talk Topics
CASUAL_TALK_TEMPLATES = [
    # 1. What is X
    ("what is {topic}", lambda topic, info: f"🤖 **Let's talk about {topic.capitalize()}!**\n\n{info['opin']}\n\n- **My perspective:** {info['feel']}"),
    # 2. Do you like X
    ("do you like {topic}", lambda topic, info: f"❤️ **Do I like {topic}?**\n\n{info['feel']}\n\n- **Opinion:** {info['opin']}"),
    # 3. Tell me about X
    ("tell me about {topic}", lambda topic, info: f"✨ **Let's discuss {topic.capitalize()}**\n\n- **Overview:** {info['opin']}\n- **Insight:** {info['feel']}"),
    # 4. Explain X
    ("explain {topic}", lambda topic, info: f"🧠 **Breaking down {topic.capitalize()}**\n\n{info['opin']}\n\n- **Concept:** {info['feel']}"),
    # 5. What do you think of X
    ("what do you think of {topic}", lambda topic, info: f"💭 **My thoughts on {topic.capitalize()}**\n\n{info['feel']}\n\n{info['opin']}"),
    # 6. Tell me a story about X
    ("tell me a story about {topic}", lambda topic, info: f"📖 **A story about {topic.capitalize()}**\n\n{info['story']}\n\n- **Moral:** {info['opin']}"),
    # 7. Tell me a joke about X
    ("tell me a joke about {topic}", lambda topic, info: f"😄 **Joke Time!**\n\n{info['joke']}\n\n*(Hope that brought a smile to your face!)*"),
    # 8. Do you have opinions on X
    ("do you have opinions on {topic}", lambda topic, info: f"⚖️ **Opinions on {topic.capitalize()}**\n\n- **My view:** {info['feel']}\n- **Analysis:** {info['opin']}"),
    # 9. Why is X important
    ("why is {topic} important", lambda topic, info: f"🚀 **Why {topic.capitalize()} matters**\n\n{info['opin']}\n\n- **Relevance:** {info['feel']}"),
    # 10. How do you feel about X
    ("how do you feel about {topic}", lambda topic, info: f"🎭 **Feelings regarding {topic.capitalize()}**\n\n{info['feel']}\n\n{info['opin']}"),
    # 11. Basics of X
    ("basics of {topic}", lambda topic, info: f"🎓 **Understanding {topic.capitalize()}**\n\n- **Definition:** {info['opin']}\n- **Summary:** {info['feel']}"),
    # 12. What is your favorite X
    ("what is your favorite {topic}", lambda topic, info: f"🌟 **My favorite {topic.capitalize()}?**\n\n- **Choice:** {info['feel']}\n- **Why:** {info['opin']}")
]

# Technical templates
TEMPLATE_FUNCTIONS = [
    ("what is {topic}", lambda topic, info: f"🐋 **{info['title']}**\n\n**Definition:** {info['def']}\n\n**Key Advantage:** {info['why']}"),
    ("how to use {topic}", lambda topic, info: f"⚙️ **Using {info['title']}**\n\n**Steps:** {info['how']}\n\n**Best Practices:** {info['best']}"),
    ("why use {topic}", lambda topic, info: f"🚀 **Why Adopt {info['title']}?**\n\n**Key Benefit:** {info['why']}\n\n**Under the hood:** {info['work']}"),
    ("explain {topic}", lambda topic, info: f"🧠 **Detailed Explanation: {info['title']}**\n\n{info['def']}\n\n- **How it works:** {info['work']}\n- **Why it matters:** {info['why']}"),
    ("what does {topic} do", lambda topic, info: f"🔧 **Functionality of {info['title']}**\n\n**Core Task:** {info['def']}\n\n**Operational Workflow:** {info['work']}"),
    ("definition of {topic}", lambda topic, info: f"📚 **Definition: {info['title']}**\n\n{info['def']}\n\n- **How to start:** {info['how']}"),
    ("tell me about {topic}", lambda topic, info: f"✨ **About {info['title']}**\n\n{info['def']}\n\n**Implementation:** {info['how']}\n\n**Pro Tip:** {info['best']}"),
    ("benefits of {topic}", lambda topic, info: f"🏆 **Benefits of {info['title']}**\n\n{info['why']}\n\n- **Production standards:** {info['best']}"),
    ("is {topic} good", lambda topic, info: f"⚖️ **Evaluating {info['title']}**\n\nYes, {info['title']} is highly regarded in modern development. {info['why']}\n\n- **Deployment guideline:** {info['best']}"),
    ("basics of {topic}", lambda topic, info: f"🎓 **Basics: {info['title']}**\n\n- **What it is:** {info['def']}\n- **How to use it:** {info['how']}"),
    ("{topic} explanation", lambda topic, info: f"📝 **Concept Breakdown: {info['title']}**\n\n{info['def']}\n\n{info['work']}"),
    ("how does {topic} work", lambda topic, info: f"⚙️ **How {info['title']} Works**\n\n{info['work']}\n\n- **Best implementation:** {info['best']}"),
    ("advantages of {topic}", lambda topic, info: f"🚀 **Advantages of {info['title']}**\n\n{info['why']}\n\n- **Operational summary:** {info['def']}"),
    ("best practices for {topic}", lambda topic, info: f"🌟 **Best Practices for {info['title']}**\n\n{info['best']}\n\n- **Setup guide:** {info['how']}"),
    ("when to use {topic}", lambda topic, info: f"🎯 **When to use {info['title']}**\n\nUse this when: {info['why']}\n\n- **Setup configuration:** {info['how']}"),
    ("how to configure {topic}", lambda topic, info: f"🔧 **Configuring {info['title']}**\n\n- **Getting Started:** {info['how']}\n- **Standards:** {info['best']}")
]

def generate_database():
    database = {}
    
    # 1. Compile 41 technical topics (41 topics * 16 templates = 656 mappings)
    for topic, info in TOPIC_DATA.items():
        for template, func in TEMPLATE_FUNCTIONS:
            q1 = template.format(topic=topic)
            a1 = func(topic, info)
            database[q1] = [a1]
            
            # Alternative: spaced out or dash variants (e.g. nextjs vs next.js)
            alt_topic = topic.replace(".", "").replace(" ", "").replace("-", "")
            if alt_topic != topic:
                q2 = template.format(topic=alt_topic)
                database[q2] = [a1]

    # 2. Compile 88 casual talk topics (88 topics * 12 templates = 1056 mappings)
    for topic, info in CASUAL_TALK_DATA.items():
        for template, func in CASUAL_TALK_TEMPLATES:
            q1 = template.format(topic=topic)
            a1 = func(topic, info)
            database[q1] = [a1]
            
            alt_topic = topic.replace(".", "").replace(" ", "").replace("-", "")
            if alt_topic != topic:
                q2 = template.format(topic=alt_topic)
                database[q2] = [a1]
                
    # 3. Compile base greetings, creator origin, and direct matches (~350 variations)
    # This expands the total unique questions database to 2000+!
    from backend.agent.hardcoded_responses import HARDCODED_QA
    for k, v in HARDCODED_QA.items():
        # Avoid overriding already generated templates
        if k not in database:
            database[k] = v
        
        # Add conversational variants
        for prefix in ["hey", "hi", "hello", "can you tell me", "do you know"]:
            var_key = f"{prefix} {k}"
            if var_key not in database:
                database[var_key] = v

    print(f"Generated a massive offline database of {len(database)} unique question mappings!")
    
    # Generate the self-contained python file content
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "hardcoded_responses.py")
    
    python_code = f"""import random
import urllib.request
import urllib.parse
import json
import re
import html

# Massive offline QA knowledge base ({len(database)} unique question mappings)
HARDCODED_QA = {repr(database)}

def search_web_fallback(query: str) -> str:
    \"\"\"
    Queries DuckDuckGo Search and extracts top search snippet results.
    This works without any API keys, completely free and offline-friendly.
    \"\"\"
    # 1. Try DuckDuckGo Instant Answer JSON API
    try:
        url = f"https://api.duckduckgo.com/?q={{urllib.parse.quote(query)}}&format=json&no_html=1"
        req = urllib.request.Request(
            url, 
            headers={{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            abstract = data.get("AbstractText")
            if abstract:
                return (
                    f"🔍 **Web Search Answer:**\\n\\n"
                    f"{{abstract}}\\n\\n"
                    f"*(Source: DuckDuckGo Instant Answer)*"
                )
    except Exception:
        pass

    # 2. Fallback to DuckDuckGo HTML Search scrape
    try:
        url = f"https://html.duckduckgo.com/html/?q={{urllib.parse.quote(query)}}"
        req = urllib.request.Request(
            url,
            headers={{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
            # Extract snippets and titles using clean regex
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL)
            titles = re.findall(r'<a class="result__url"[^>]*>(.*?)</a>', html_content, re.DOTALL)
            
            if snippets:
                formatted = f"🔍 **Web Search Results for '{{query}}':**\\n\\n"
                count = 0
                for title, snippet in zip(titles, snippets):
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    clean_snippet = html.unescape(clean_snippet)
                    clean_title = html.unescape(clean_title)
                    
                    # Cleanup spaces
                    clean_snippet = re.sub(r'\\s+', ' ', clean_snippet)
                    clean_title = re.sub(r'\\s+', ' ', clean_title)
                    
                    if clean_snippet:
                        formatted += f"* **{{clean_title}}**: {{clean_snippet}}\\n\\n"
                        count += 1
                        if count >= 3:
                            break
                return formatted + "*(Source: DuckDuckGo Web Search)*"
    except Exception as e:
        print(f"Scraper error: {{e}}")
        
    return (
        f"⚠️ **Offline Search Failed:** I couldn't find a local answer or fetch web results for '{{query}}'.\\n\\n"
        f"Please check your internet connection, or set a **Gemini API Key** in Settings (gear icon ⚙️) to unlock full capability."
    )

def get_hardcoded_response(message: str) -> str:
    \"\"\"
    Matches the user message against standard offline QA keys.
    Returns a random rotating response if matched, otherwise None.
    \"\"\"
    if not message:
        return None
        
    # Clean the input query for matching
    cleaned = message.strip().lower().replace("?", "").replace(".", "").replace("!", "").strip()
    
    # Substring / pattern matching
    for key, responses in HARDCODED_QA.items():
        if cleaned == key or cleaned.startswith(key + " ") or (" " + key + " ") in (" " + cleaned + " ") or cleaned.endswith(" " + key):
            return random.choice(responses)
            
    return None
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(python_code)
    print("Successfully wrote hardcoded_responses.py!")

if __name__ == "__main__":
    generate_database()
