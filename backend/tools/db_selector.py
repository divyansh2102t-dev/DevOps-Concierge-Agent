DB_CONFIGS = {
    "postgresql": {
        "name": "PostgreSQL",
        "keywords": ["postgres", "postgresql", "relational", "sql", "prisma"],
        "env_vars": ["DATABASE_URL"],
        "files": {
            "prisma/schema.prisma": lambda db_url: f"""generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "postgresql"
  url      = env("DATABASE_URL")
}}
""",
            ".env.example": lambda db_url: 'DATABASE_URL="postgresql://user:password@localhost:5432/mydb"\n'
        }
    },
    "mongodb": {
        "name": "MongoDB",
        "keywords": ["mongo", "mongodb", "nosql", "document"],
        "env_vars": ["MONGODB_URI"],
        "files": {
            "lib/mongodb.js": lambda db_url: """import { MongoClient } from 'mongodb'

const uri = process.env.MONGODB_URI
const options = {}

let client
let clientPromise

if (!process.env.MONGODB_URI) {
  throw new Error('Please add MONGODB_URI to .env')
}

if (process.env.NODE_ENV === 'development') {
  if (!global._mongoClientPromise) {
    client = new MongoClient(uri, options)
    global._mongoClientPromise = client.connect()
  }
  clientPromise = global._mongoClientPromise
} else {
  client = new MongoClient(uri, options)
  clientPromise = client.connect()
}

export default clientPromise
""",
            ".env.example": lambda db_url: 'MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/mydb"\n'
        }
    },
    "sqlite": {
        "name": "SQLite",
        "keywords": ["sqlite", "local", "simple", "lightweight", "file"],
        "env_vars": ["DATABASE_URL"],
        "files": {
            "prisma/schema.prisma": lambda db_url: """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}
""",
            ".env.example": lambda db_url: 'DATABASE_URL="file:./dev.db"\n'
        }
    },
    "supabase": {
        "name": "Supabase",
        "keywords": ["supabase", "realtime", "auth", "backend-as-a-service"],
        "env_vars": ["NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"],
        "files": {
            "lib/supabase.js": lambda db_url: """import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
""",
            ".env.example": lambda db_url: 'NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"\nNEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"\n'
        }
    }
}


def select_database(requirements_text):
    requirements_lower = requirements_text.lower()
    scores = {}
    for db_id, config in DB_CONFIGS.items():
        score = sum(1 for kw in config["keywords"] if kw in requirements_lower)
        scores[db_id] = score

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "postgresql"

    return {
        "selected": best,
        "name": DB_CONFIGS[best]["name"],
        "env_vars": DB_CONFIGS[best]["env_vars"],
        "scores": scores
    }


def generate_db_files(db_type, project_dir):
    import os
    if db_type not in DB_CONFIGS:
        return {"success": False, "error": f"Unknown database type: {db_type}"}

    config = DB_CONFIGS[db_type]
    created = []
    for rel_path, generator in config["files"].items():
        full_path = os.path.join(project_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(generator(""))
        created.append(rel_path)

    return {"success": True, "database": db_type, "files_created": created}
