<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 900" width="800" height="900">
  <!-- Fond -->
  <rect width="800" height="900" fill="#f8f9fa" />
  
  <!-- Titre -->
  <g>
    <rect x="40" y="30" width="720" height="80" rx="10" fill="#3498db" />
    <text x="400" y="80" font-family="Arial" font-size="32" font-weight="bold" text-anchor="middle" fill="white">Projet GoodAir - TotalGreen</text>
  </g>
  
  <!-- Logo -->
  <g transform="translate(80, 140)">
    <circle cx="40" cy="40" r="40" fill="#2ecc71" />
    <path d="M32,52 C32,52 48,28 64,52 M24,64 C24,64 56,16 72,64" stroke="white" stroke-width="5" fill="none" />
    <text x="100" y="40" font-family="Arial" font-size="24" font-weight="bold" fill="#2c3e50">GoodAir</text>
    <text x="100" y="70" font-family="Arial" font-size="14" fill="#7f8c8d">Laboratoire de recherche pour la qualité de l'air et de l'eau</text>
  </g>
  
  <!-- Objectif -->
  <g>
    <rect x="80" y="220" width="640" height="80" rx="10" fill="#ecf0f1" stroke="#bdc3c7" stroke-width="2" />
    <text x="100" y="250" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">Objectif du Projet</text>
    <text x="100" y="275" font-family="Arial" font-size="14" fill="#7f8c8d">Analyser la qualité de l'air et de l'eau en France pour proposer des recommandations,</text>
    <text x="100" y="295" font-family="Arial" font-size="14" fill="#7f8c8d">étudier les impacts du changement climatique et établir des seuils d'alerte.</text>
  </g>
  
  <!-- Architecture -->
  <g>
    <rect x="80" y="320" width="640" height="320" rx="10" fill="#ecf0f1" stroke="#bdc3c7" stroke-width="2" />
    <text x="100" y="350" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">Architecture Technique</text>
    
    <!-- Diagramme d'architecture -->
    <g transform="translate(120, 370)">
      <!-- Sources de données -->
      <rect x="0" y="0" width="140" height="70" rx="5" fill="#3498db" />
      <text x="70" y="25" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">Sources de données</text>
      <text x="70" y="45" font-family="Arial" font-size="10" text-anchor="middle" fill="white">API AQICN (Air)</text>
      <text x="70" y="60" font-family="Arial" font-size="10" text-anchor="middle" fill="white">API OpenWeatherMap</text>
      
      <!-- Flèche -->
      <path d="M150,35 L180,35" stroke="#7f8c8d" stroke-width="2" fill="none" marker-end="url(#arrow)" />
      
      <!-- Ingestion -->
      <rect x="190" y="0" width="120" height="70" rx="5" fill="#2ecc71" />
      <text x="250" y="25" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">Ingestion</text>
      <text x="250" y="45" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Apache Airflow</text>
      <text x="250" y="60" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Python + Kafka</text>
      
      <!-- Flèche -->
      <path d="M250,80 L250,110" stroke="#7f8c8d" stroke-width="2" fill="none" marker-end="url(#arrow)" />
      
      <!-- Stockage -->
      <rect x="150" y="120" width="200" height="70" rx="5" fill="#e74c3c" />
      <text x="250" y="145" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">Stockage</text>
      <text x="250" y="165" font-family="Arial" font-size="10" text-anchor="middle" fill="white">MinIO (Data Lake) + PostgreSQL</text>
      
      <!-- Flèche -->
      <path d="M250,200 L250,230" stroke="#7f8c8d" stroke-width="2" fill="none" marker-end="url(#arrow)" />
      
      <!-- Traitement -->
      <rect x="170" y="240" width="160" height="70" rx="5" fill="#9b59b6" />
      <text x="250" y="265" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">Traitement</text>
      <text x="250" y="285" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Python + Pandas + ETL</text>
      <text x="250" y="300" font-family="Arial" font-size="10" text-anchor="middle" fill="white">dbt (tests qualité)</text>
      
      <!-- Flèche vers Visualisation -->
      <path d="M340,275 L380,275" stroke="#7f8c8d" stroke-width="2" fill="none" marker-end="url(#arrow)" />
      
      <!-- Visualisation -->
      <rect x="390" y="240" width="120" height="70" rx="5" fill="#f39c12" />
      <text x="450" y="265" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle" fill="white">Visualisation</text>
      <text x="450" y="285" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Power BI</text>
      <text x="450" y="300" font-family="Arial" font-size="10" text-anchor="middle" fill="white">Tableau</text>
    </g>
    
    <!-- Marqueur flèche -->
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="#7f8c8d" />
      </marker>
    </defs>
  </g>
  
  <!-- Technologies -->
  <g>
    <rect x="80" y="660" width="640" height="200" rx="10" fill="#ecf0f1" stroke="#bdc3c7" stroke-width="2" />
    <text x="100" y="690" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">Technologies Clés</text>
    
    <!-- Colonne 1 -->
    <g transform="translate(100, 705)">
      <circle cx="12" cy="12" r="8" fill="#3498db" />
      <text x="30" y="16" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Collecte</text>
      <text x="30" y="35" font-family="Arial" font-size="12" fill="#7f8c8d">• Apache Airflow</text>
      <text x="30" y="55" font-family="Arial" font-size="12" fill="#7f8c8d">• Python (Requests)</text>
      <text x="30" y="75" font-family="Arial" font-size="12" fill="#7f8c8d">• Apache Kafka</text>
      
      <circle cx="12" cy="105" r="8" fill="#9b59b6" />
      <text x="30" y="110" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Sécurité</text>
      <text x="30" y="130" font-family="Arial" font-size="12" fill="#7f8c8d">• Keycloak</text>
      <text x="30" y="150" font-family="Arial" font-size="12" fill="#7f8c8d">• Hébergement UE</text>
    </g>
    
    <!-- Colonne 2 -->
    <g transform="translate(310, 705)">
      <circle cx="12" cy="12" r="8" fill="#e74c3c" />
      <text x="30" y="16" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Stockage</text>
      <text x="30" y="35" font-family="Arial" font-size="12" fill="#7f8c8d">• MinIO (Data Lake)</text>
      <text x="30" y="55" font-family="Arial" font-size="12" fill="#7f8c8d">• PostgreSQL</text>
      <text x="30" y="75" font-family="Arial" font-size="12" fill="#7f8c8d">• RDS/Cloud SQL</text>
      
      <circle cx="12" cy="105" r="8" fill="#f39c12" />
      <text x="30" y="110" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Visualisation</text>
      <text x="30" y="130" font-family="Arial" font-size="12" fill="#7f8c8d">• Power BI</text>
      <text x="30" y="150" font-family="Arial" font-size="12" fill="#7f8c8d">• API REST (FastAPI)</text>
    </g>
    
    <!-- Colonne 3 -->
    <g transform="translate(520, 705)">
      <circle cx="12" cy="12" r="8" fill="#27ae60" />
      <text x="30" y="16" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Traitement</text>
      <text x="30" y="35" font-family="Arial" font-size="12" fill="#7f8c8d">• Python Pandas</text>
      <text x="30" y="55" font-family="Arial" font-size="12" fill="#7f8c8d">• dbt (tests qualité)</text>
      <text x="30" y="75" font-family="Arial" font-size="12" fill="#7f8c8d">• Scikit-learn (ML)</text>
      
      <circle cx="12" cy="105" r="8" fill="#8e44ad" />
      <text x="30" y="110" font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">Infrastructure</text>
      <text x="30" y="130" font-family="Arial" font-size="12" fill="#7f8c8d">• Docker</text>
      <text x="30" y="150" font-family="Arial" font-size="12" fill="#7f8c8d">• CI/CD</text>
    </g>
  </g>
  
  <!-- Méthodologie -->
  <g>
    <rect x="80" y="880" width="640" height="40" rx="5" fill="#34495e" />
    <text x="400" y="905" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="white">Méthodologie Agile/Scrum • Équipe de 4 personnes • Délai: Juin 2025</text>
  </g>
</svg>
