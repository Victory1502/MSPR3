import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import folium
from streamlit_folium import st_folium

# Configuration de la page
st.set_page_config(
    page_title="Analyse Météo & Qualité de l'Air - France",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .alert-danger { background-color: #f8d7da; border-left: 5px solid #dc3545; }
    .alert-warning { background-color: #fff3cd; border-left: 5px solid #ffc107; }
    .alert-success { background-color: #d4edda; border-left: 5px solid #28a745; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Charge et nettoie les données"""
    try:
        # Charger le fichier CSV
        df = pd.read_csv('data.csv')
        
        # Nettoyer les noms de colonnes
        df.columns = df.columns.str.strip()
        
        # Convertir les timestamps
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df['Horodatage AQI'] = pd.to_datetime(df['Horodatage AQI'])
        df['Date'] = df['Timestamp'].dt.date
        df['Heure'] = df['Timestamp'].dt.hour
        df['Date_AQI'] = df['Horodatage AQI'].dt.date
        
        # Ajouter des colonnes calculées
        df['Confort_Thermique'] = df['Température (°C)'].apply(
            lambda x: 'Optimal' if 18 <= x <= 24 else 
                     'Chaud' if x > 24 else 'Froid'
        )
        
        df['Qualite_Air'] = df['AQI'].apply(
            lambda x: 'Excellent' if x <= 50 else
                     'Bon' if x <= 100 else
                     'Modéré' if x <= 150 else 'Mauvais'
        )
        
        # Ajouter un indice de confort global (0-100)
        df['Indice_Confort'] = (
            # Score température (optimal 20-22°C)
            (100 - abs(df['Température (°C)'] - 21) * 3).clip(0, 100) * 0.3 +
            # Score AQI (inverse)
            (100 - df['AQI']).clip(0, 100) * 0.3 +
            # Score humidité (optimal 45-55%)
            (100 - abs(df['Humidité (%)'] - 50) * 2).clip(0, 100) * 0.2 +
            # Score vent (optimal 2-8 m/s)
            (100 - abs(df['Vitesse du vent (m/s)'] - 5) * 10).clip(0, 100) * 0.2
        ).round(1)
        
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        st.info("Vérifiez que le fichier 'data.csv' est présent dans le répertoire de l'application.")
        return None

def create_aqi_gauge(aqi_value, title="AQI"):
    """Crée un graphique en jauge pour l'AQI"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = aqi_value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 200]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgreen"},
                {'range': [50, 100], 'color': "yellow"},
                {'range': [100, 150], 'color': "orange"},
                {'range': [150, 200], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 150
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

def create_temperature_map(df):
    """Crée une carte de températures"""
    # Centre de la France
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6)
    
    # Ajouter les points pour chaque ville
    for _, row in df.iterrows():
        # Couleur selon la température
        temp = row['Température (°C)']
        if temp < 20:
            color = 'blue'
        elif temp < 25:
            color = 'green'
        elif temp < 30:
            color = 'orange'
        else:
            color = 'red'
        
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=10,
            popup=f"""
            <b>{row['Ville']}</b><br>
            Température: {temp}°C<br>
            AQI: {row['AQI']}<br>
            Humidité: {row['Humidité (%)']}%
            """,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7
        ).add_to(m)
    
    return m

def main():
    # Titre principal
    st.markdown('<h1 class="main-header">🌡️ Analyse Météo & Qualité de l\'Air - France</h1>', 
                unsafe_allow_html=True)
    
    # Chargement des données
    df = load_data()
    
    if df is None:
        st.error("❌ Impossible de charger les données. Vérifiez que le fichier 'data.csv' est présent.")
        st.info("📁 Le fichier doit être nommé exactement 'data.csv' et placé dans le même répertoire que cette application.")
        return
    
    # Sidebar - Filtres
    st.sidebar.header("🔧 Filtres & Options")
    
    # Informations sur le dataset
    st.sidebar.info(f"""
    📊 **Dataset Info**
    - 🏙️ {len(df['Ville'].unique())} villes
    - 📅 {len(df['Date'].unique())} dates
    - 📈 {len(df)} mesures totales
    - 🕐 Période: {df['Date'].min()} au {df['Date'].max()}
    """)
    
    # Sélection des villes
    villes_disponibles = sorted(df['Ville'].unique())
    villes_selectionnees = st.sidebar.multiselect(
        "🏙️ Sélectionner les villes",
        options=villes_disponibles,
        default=villes_disponibles[:6]  # Top 6 par défaut
    )
    
    # Sélection de la date
    dates_disponibles = sorted(df['Date'].unique())
    date_selectionnee = st.sidebar.selectbox(
        "📅 Sélectionner une date",
        options=dates_disponibles,
        index=len(dates_disponibles)-1  # Dernière date par défaut
    )
    
    # Options d'affichage
    st.sidebar.subheader("🎛️ Options d'affichage")
    show_aqi_details = st.sidebar.checkbox("Afficher détails AQI", True)
    show_comfort_index = st.sidebar.checkbox("Afficher indice de confort", True)
    show_wind_analysis = st.sidebar.checkbox("Afficher analyse du vent", True)
    
    # Filtrer les données
    df_filtered = df[
        (df['Ville'].isin(villes_selectionnees)) & 
        (df['Date'] == date_selectionnee)
    ]
    
    if df_filtered.empty:
        st.warning("⚠️ Aucune donnée disponible pour la sélection actuelle.")
        return
    
    # ============ MÉTRIQUES GÉNÉRALES ============
    st.header("📊 Vue d'ensemble")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        temp_moy = df_filtered['Température (°C)'].mean()
        temp_min = df_filtered['Température (°C)'].min()
        temp_max = df_filtered['Température (°C)'].max()
        st.metric(
            label="🌡️ Température",
            value=f"{temp_moy:.1f}°C",
            delta=f"Min: {temp_min:.1f}°C | Max: {temp_max:.1f}°C"
        )
    
    with col2:
        aqi_moy = df_filtered['AQI'].mean()
        aqi_status = "Excellent" if aqi_moy <= 50 else "Bon" if aqi_moy <= 100 else "Modéré" if aqi_moy <= 150 else "Mauvais"
        st.metric(
            label="🌬️ AQI Moyen",
            value=f"{aqi_moy:.0f}",
            delta=aqi_status
        )
    
    with col3:
        humid_moy = df_filtered['Humidité (%)'].mean()
        humid_status = "Confortable" if 40 <= humid_moy <= 60 else "Sec" if humid_moy < 40 else "Humide"
        st.metric(
            label="💧 Humidité",
            value=f"{humid_moy:.0f}%",
            delta=humid_status
        )
    
    with col4:
        vent_moy = df_filtered['Vitesse du vent (m/s)'].mean()
        vent_status = "Calme" if vent_moy < 5 else "Modéré" if vent_moy < 10 else "Fort"
        st.metric(
            label="💨 Vent Moyen",
            value=f"{vent_moy:.1f} m/s",
            delta=vent_status
        )
    
    with col5:
        if show_comfort_index:
            confort_moy = df_filtered['Indice_Confort'].mean()
            confort_status = "Excellent" if confort_moy >= 80 else "Bon" if confort_moy >= 60 else "Moyen" if confort_moy >= 40 else "Faible"
            st.metric(
                label="⭐ Confort Global",
                value=f"{confort_moy:.0f}/100",
                delta=confort_status
            )
    
    # ============ ALERTES ============
    st.header("⚠️ Alertes & Recommandations")
    
    # Alerte pollution
    pollution_critique = df_filtered[df_filtered['AQI'] > 100]
    if not pollution_critique.empty:
        villes_polluees = pollution_critique['Ville'].tolist()
        st.markdown(f"""
        <div class="alert-box alert-danger">
            <strong>🚨 Alerte Pollution :</strong> Qualité de l'air dégradée dans : {', '.join(villes_polluees)}
            <br><strong>Recommandation :</strong> Éviter les activités sportives extérieures intensives.
        </div>
        """, unsafe_allow_html=True)
    
    # Alerte température
    temp_extreme = df_filtered[df_filtered['Température (°C)'] > 30]
    if not temp_extreme.empty:
        st.markdown(f"""
        <div class="alert-box alert-warning">
            <strong>🔥 Alerte Chaleur :</strong> Températures élevées détectées (max: {df_filtered['Température (°C)'].max():.1f}°C)
            <br><strong>Recommandation :</strong> Éviter l'exposition au soleil entre 11h et 16h.
        </div>
        """, unsafe_allow_html=True)
    
    # Conditions optimales
    conditions_ok = df_filtered[
        (df_filtered['AQI'] <= 50) & 
        (df_filtered['Température (°C)'].between(18, 25))
    ]
    if not conditions_ok.empty:
        villes_ok = conditions_ok['Ville'].tolist()
        st.markdown(f"""
        <div class="alert-box alert-success">
            <strong>✅ Conditions Optimales :</strong> {', '.join(villes_ok)}
            <br><strong>Recommandation :</strong> Conditions idéales pour toutes activités extérieures.
        </div>
        """, unsafe_allow_html=True)
    
    # ============ GRAPHIQUES PRINCIPAUX ============
    st.header("📈 Analyses Principales")
    
    # Row 1: Températures et AQI
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌡️ Températures par Ville")
        fig_temp = px.bar(
            df_filtered.sort_values('Température (°C)', ascending=False),
            x='Ville',
            y='Température (°C)',
            color='Température (°C)',
            color_continuous_scale='RdYlBu_r',
            title="Températures actuelles (classées)",
            text='Température (°C)',
            hover_data=['Température ressentie (°C)', 'Humidité (%)']
        )
        fig_temp.update_traces(texttemplate='%{text:.1f}°C', textposition='outside')
        fig_temp.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_temp, use_container_width=True)
    
    with col2:
        st.subheader("🌬️ Qualité de l'Air (AQI)")
        fig_aqi = px.bar(
            df_filtered.sort_values('AQI', ascending=False),
            x='Ville',
            y='AQI',
            color='AQI',
            color_continuous_scale=['green', 'yellow', 'orange', 'red'],
            title="Indice de Qualité de l'Air (classé)",
            text='AQI',
            hover_data=['Polluant dominant', 'PM2.5', 'PM10']
        )
        fig_aqi.update_traces(texttemplate='%{text}', textposition='outside')
        fig_aqi.add_hline(y=50, line_dash="dash", line_color="green", 
                         annotation_text="Seuil Bon (50)")
        fig_aqi.add_hline(y=100, line_dash="dash", line_color="orange", 
                         annotation_text="Seuil Modéré (100)")
        fig_aqi.add_hline(y=150, line_dash="dash", line_color="red", 
                         annotation_text="Seuil Mauvais (150)")
        fig_aqi.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_aqi, use_container_width=True)
    
    # Row 2: Indice de confort et conditions météo
    if show_comfort_index:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⭐ Indice de Confort Global")
            fig_comfort = px.bar(
                df_filtered.sort_values('Indice_Confort', ascending=False),
                x='Ville',
                y='Indice_Confort',
                color='Indice_Confort',
                color_continuous_scale='RdYlGn',
                title="Indice de Confort (0-100)",
                text='Indice_Confort',
                range_y=[0, 100]
            )
            fig_comfort.update_traces(texttemplate='%{text:.0f}', textposition='outside')
            fig_comfort.add_hline(y=80, line_dash="dash", line_color="green", 
                                 annotation_text="Excellent (80+)")
            fig_comfort.add_hline(y=60, line_dash="dash", line_color="orange", 
                                 annotation_text="Bon (60+)")
            fig_comfort.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_comfort, use_container_width=True)
        
        with col2:
            st.subheader("🌤️ Conditions Météorologiques")
            condition_counts = df_filtered['Condition météo'].value_counts()
            fig_conditions = px.pie(
                values=condition_counts.values,
                names=condition_counts.index,
                title="Répartition des Conditions Météo",
                hole=0.4
            )
            fig_conditions.update_layout(height=400)
            st.plotly_chart(fig_conditions, use_container_width=True)
    
    # ============ CARTE INTERACTIVE ============
    st.subheader("🗺️ Carte Interactive - Températures")
    
    # Créer la carte
    temperature_map = create_temperature_map(df_filtered)
    
    # Afficher la carte
    map_data = st_folium(temperature_map, width=700, height=500)
    
    # ============ ANALYSE DÉTAILLÉE ============
    st.header("📊 Analyses Détaillées")
    
    # Onglets pour différentes analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌡️ Confort Thermique", "🌬️ Polluants", "💨 Conditions Vent", "📊 Corrélations", "🏆 Classements"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution du confort thermique
            confort_counts = df_filtered['Confort_Thermique'].value_counts()
            fig_confort = px.pie(
                values=confort_counts.values,
                names=confort_counts.index,
                title="Répartition du Confort Thermique",
                color_discrete_map={
                    'Optimal': 'green',
                    'Chaud': 'red', 
                    'Froid': 'blue'
                }
            )
            st.plotly_chart(fig_confort, use_container_width=True)
        
        with col2:
            # Température ressentie vs réelle
            fig_ressenti = px.scatter(
                df_filtered,
                x='Température (°C)',
                y='Température ressentie (°C)',
                color='Ville',
                size='Humidité (%)',
                title="Température Ressentie vs Réelle",
                hover_data=['Humidité (%)', 'Vitesse du vent (m/s)']
            )
            fig_ressenti.add_line(x=[15, 35], y=[15, 35], line_color="red", 
                                 line_dash="dash", name="Ligne d'égalité")
            st.plotly_chart(fig_ressenti, use_container_width=True)
        
        # Analyse détaillée du confort
        st.subheader("📋 Analyse Détaillée du Confort")
        comfort_df = df_filtered[['Ville', 'Température (°C)', 'Température ressentie (°C)', 
                                 'Humidité (%)', 'Indice_Confort', 'Confort_Thermique']].copy()
        comfort_df['Écart_Ressenti'] = comfort_df['Température ressentie (°C)'] - comfort_df['Température (°C)']
        st.dataframe(comfort_df.sort_values('Indice_Confort', ascending=False), use_container_width=True)
    
    with tab2:
        if show_aqi_details:
            # Analyse des polluants
            polluants_cols = ['PM2.5', 'PM10', 'O3', 'NO2']
            df_polluants = df_filtered[['Ville'] + polluants_cols].dropna()
            
            if not df_polluants.empty:
                fig_polluants = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=polluants_cols,
                    specs=[[{"secondary_y": False}, {"secondary_y": False}],
                           [{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                for i, polluant in enumerate(polluants_cols):
                    row = i // 2 + 1
                    col = i % 2 + 1
                    
                    fig_polluants.add_trace(
                        go.Bar(x=df_polluants['Ville'], y=df_polluants[polluant], 
                              name=polluant, showlegend=False),
                        row=row, col=col
                    )
                
                fig_polluants.update_layout(height=600, title_text="Concentration des Polluants (µg/m³)")
                st.plotly_chart(fig_polluants, use_container_width=True)
                
                # Tableau des polluants dominants
                st.subheader("🔍 Polluants Dominants par Ville")
                polluant_analysis = df_filtered[['Ville', 'AQI', 'Polluant dominant'] + polluants_cols]
                st.dataframe(polluant_analysis.sort_values('AQI', ascending=False), use_container_width=True)
            else:
                st.info("Données de polluants non disponibles pour la sélection actuelle.")
        else:
            st.info("Activez 'Afficher détails AQI' dans les options pour voir cette analyse.")
    
    with tab3:
        if show_wind_analysis:
            col1, col2 = st.columns(2)
            
            with col1:
                # Rose des vents
                fig_vent = px.bar_polar(
                    df_filtered,
                    r='Vitesse du vent (m/s)',
                    theta='Direction du vent (°)',
                    color='Ville',
                    title="Rose des Vents",
                    template="plotly_white"
                )
                st.plotly_chart(fig_vent, use_container_width=True)
            
            with col2:
                # Relation vent-température
                fig_vent_temp = px.scatter(
                    df_filtered,
                    x='Vitesse du vent (m/s)',
                    y='Température (°C)',
                    color='Ville',
                    size='Humidité (%)',
                    title="Relation Vent - Température",
                    hover_data=['Direction du vent (°)']
                )
                st.plotly_chart(fig_vent_temp, use_container_width=True)
            
            # Analyse du vent par direction
            st.subheader("🧭 Analyse du Vent par Direction")
            df_filtered['Direction_Cardinale'] = df_filtered['Direction du vent (°)'].apply(
                lambda x: 'Nord' if 337.5 <= x or x < 22.5 else
                         'Nord-Est' if 22.5 <= x < 67.5 else
                         'Est' if 67.5 <= x < 112.5 else
                         'Sud-Est' if 112.5 <= x < 157.5 else
                         'Sud' if 157.5 <= x < 202.5 else
                         'Sud-Ouest' if 202.5 <= x < 247.5 else
                         'Ouest' if 247.5 <= x < 292.5 else 'Nord-Ouest'
            )
            wind_analysis = df_filtered.groupby('Direction_Cardinale').agg({
                'Vitesse du vent (m/s)': ['mean', 'max'],
                'Ville': 'count'
            }).round(2)
            st.dataframe(wind_analysis, use_container_width=True)
        else:
            st.info("Activez 'Afficher analyse du vent' dans les options pour voir cette analyse.")
    
    with tab4:
        # Matrice de corrélation
        numeric_cols = ['Température (°C)', 'Température ressentie (°C)', 'Pression (hPa)', 
                       'Humidité (%)', 'Vitesse du vent (m/s)', 'Couverture nuageuse (%)', 
                       'AQI', 'Indice_Confort']
        df_corr = df_filtered[numeric_cols].corr()
        
        fig_corr = px.imshow(
            df_corr,
            text_auto='.2f',
            title="Matrice de Corrélation",
            color_continuous_scale='RdBu',
            aspect="auto"
        )
        fig_corr.update_layout(height=600)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Insights automatiques
        st.subheader("🔍 Insights Automatiques")
        
        # Corrélations significatives
        strong_corrs = []
        for i in range(len(df_corr.columns)):
            for j in range(i+1, len(df_corr.columns)):
                corr_val = df_corr.iloc[i, j]
                if abs(corr_val) > 0.5:
                    strong_corrs.append((df_corr.columns[i], df_corr.columns[j], corr_val))
        
        if strong_corrs:
            st.write("**Corrélations significatives (|r| > 0.5) :**")
            for var1, var2, corr in strong_corrs:
                corr_type = "positive" if corr > 0 else "négative"
                st.write(f"• {var1} ↔ {var2}: {corr:.2f} ({corr_type})")
        
        # Ville la plus polluée
        if not df_filtered.empty:
            ville_max_aqi = df_filtered.loc[df_filtered['AQI'].idxmax(), 'Ville']
            aqi_max = df_filtered['AQI'].max()
            st.warning(f"🏭 Ville la plus polluée : **{ville_max_aqi}** (AQI: {aqi_max})")
            
            # Ville avec meilleures conditions
            ville_best_comfort = df_filtered.loc[df_filtered['Indice_Confort'].idxmax(), 'Ville']
            comfort_max = df_filtered['Indice_Confort'].max()
            st.success(f"⭐ Meilleures conditions : **{ville_best_comfort}** (Confort: {comfort_max:.0f}/100)")
    
    with tab5:
        st.subheader("🏆 Classements des Villes")
        
        # Créer les classements
        rankings = df_filtered.groupby('Ville').agg({
            'Température (°C)': 'mean',
            'AQI': 'mean',
            'Humidité (%)': 'mean',
            'Vitesse du vent (m/s)': 'mean',
            'Indice_Confort': 'mean'
        }).round(1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🌡️ Top Températures (les plus chaudes)**")
            temp_ranking = rankings.sort_values('Température (°C)', ascending=False)
            for i, (ville, data) in enumerate(temp_ranking.head(5).iterrows(), 1):
                st.write(f"{i}. {ville}: {data['Température (°C)']}°C")
            
            st.write("**🌬️ Top Qualité de l'Air (AQI le plus bas)**")
            aqi_ranking = rankings.sort_values('AQI', ascending=True)
            for i, (ville, data) in enumerate(aqi_ranking.head(5).iterrows(), 1):
                st.write(f"{i}. {ville}: AQI {data['AQI']:.0f}")
        
        with col2:
            st.write("**⭐ Top Confort Global**")
            comfort_ranking = rankings.sort_values('Indice_Confort', ascending=False)
            for i, (ville, data) in enumerate(comfort_ranking.head(5).iterrows(), 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                st.write(f"{medal} {ville}: {data['Indice_Confort']:.0f}/100")
            
            st.write("**💨 Conditions de Vent (vitesse modérée)**")
            # Vent optimal entre 2-8 m/s
            rankings['Vent_Score'] = rankings['Vitesse du vent (m/s)'].apply(
                lambda x: max(0, 100 - abs(x - 5) * 10)
            )
            vent_ranking = rankings.sort_values('Vent_Score', ascending=False)
            for i, (ville, data) in enumerate(vent_ranking.head(5).iterrows(), 1):
                st.write(f"{i}. {ville}: {data['Vitesse du vent (m/s)']} m/s")
        
        # Tableau de classement complet
        st.subheader("📊 Tableau de Classement Complet")
        display_rankings = rankings.copy()
        display_rankings = display_rankings.sort_values('Indice_Confort', ascending=False)
        display_rankings.index.name = 'Ville'
        st.dataframe(display_rankings, use_container_width=True)
    
    # ============ PRÉDICTIONS ET TENDANCES ============
    st.header("🔮 Analyse Prédictive et Tendances")
    
    # Analyse temporelle si plusieurs dates disponibles
    if len(df['Date'].unique()) > 1:
        st.subheader("📈 Évolution Temporelle")
        
        # Évolution des principales métriques
        evolution_df = df.groupby('Date').agg({
            'Température (°C)': 'mean',
            'AQI': 'mean',
            'Humidité (%)': 'mean',
            'Indice_Confort': 'mean'
        }).reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_temp_evolution = px.line(
                evolution_df,
                x='Date',
                y='Température (°C)',
                title="Évolution de la Température Moyenne",
                markers=True
            )
            fig_temp_evolution.update_layout(height=350)
            st.plotly_chart(fig_temp_evolution, use_container_width=True)
        
        with col2:
            fig_aqi_evolution = px.line(
                evolution_df,
                x='Date',
                y='AQI',
                title="Évolution de l'AQI Moyen",
                markers=True,
                color_discrete_sequence=['red']
            )
            fig_aqi_evolution.add_hline(y=50, line_dash="dash", line_color="green")
            fig_aqi_evolution.add_hline(y=100, line_dash="dash", line_color="orange")
            fig_aqi_evolution.update_layout(height=350)
            st.plotly_chart(fig_aqi_evolution, use_container_width=True)
        
        # Prédiction simple (tendance linéaire)
        if len(evolution_df) >= 2:
            try:
                from scipy import stats
                has_scipy = True
            except ImportError:
                has_scipy = False
                st.info("📦 Installez scipy pour les analyses de tendance : `pip install scipy`")
            
            if has_scipy:
                st.subheader("🎯 Tendances Prévisionnelles")
                
                # Calcul des tendances
                x_values = range(len(evolution_df))
                temp_slope, temp_intercept, temp_r, _, _ = stats.linregress(x_values, evolution_df['Température (°C)'])
                aqi_slope, aqi_intercept, aqi_r, _, _ = stats.linregress(x_values, evolution_df['AQI'])
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    temp_trend = "↗️ Hausse" if temp_slope > 0.1 else "↘️ Baisse" if temp_slope < -0.1 else "➡️ Stable"
                    st.metric(
                        "🌡️ Tendance Température",
                        temp_trend,
                        f"{temp_slope:.2f}°C/jour"
                    )
                
                with col2:
                    aqi_trend = "↗️ Dégradation" if aqi_slope > 1 else "↘️ Amélioration" if aqi_slope < -1 else "➡️ Stable"
                    st.metric(
                        "🌬️ Tendance AQI",
                        aqi_trend,
                        f"{aqi_slope:.1f} pts/jour"
                    )
                
                with col3:
                    # Prédiction pour demain
                    next_temp = temp_intercept + temp_slope * len(evolution_df)
                    next_aqi = max(0, aqi_intercept + aqi_slope * len(evolution_df))
                    st.metric(
                        "🔮 Prédiction J+1",
                        f"T: {next_temp:.1f}°C",
                        f"AQI: {next_aqi:.0f}"
                    )
    
    # ============ RECOMMANDATIONS INTELLIGENTES ============
    st.header("💡 Recommandations Intelligentes")
    
    # Analyser les données pour générer des recommandations
    best_cities_air = df_filtered.nsmallest(3, 'AQI')['Ville'].tolist()
    best_cities_comfort = df_filtered.nlargest(3, 'Indice_Confort')['Ville'].tolist()
    worst_cities_air = df_filtered.nlargest(2, 'AQI')['Ville'].tolist()
    
    # Recommandations par catégorie
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Recommandations Positives")
        
        if best_cities_air:
            st.success(f"🌬️ **Qualité d'air excellente** à {', '.join(best_cities_air)} - Idéal pour activités sportives extérieures")
        
        if best_cities_comfort:
            st.success(f"⭐ **Conditions optimales** à {', '.join(best_cities_comfort)} - Parfait pour sorties en famille")
        
        # Recommandations selon l'heure
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 9:
            st.info("🌅 **Matinée** : Conditions généralement optimales pour jogging et activités extérieures")
        elif 10 <= current_hour <= 16:
            st.info("☀️ **Journée** : Attention aux pics de température et pollution. Privilégier zones ombragées")
        elif 17 <= current_hour <= 20:
            st.info("🌆 **Soirée** : Bonne période pour sorties, températures plus clémentes")
        else:
            st.info("🌙 **Nuit** : Période de repos pour l'environnement, qualité d'air généralement meilleure")
    
    with col2:
        st.subheader("⚠️ Alertes et Précautions")
        
        if worst_cities_air:
            max_aqi_city = df_filtered.loc[df_filtered['AQI'].idxmax()]
            st.warning(f"🚨 **Pollution élevée** à {max_aqi_city['Ville']} (AQI: {max_aqi_city['AQI']}) - Éviter activités intenses")
        
        # Alertes température
        hot_cities = df_filtered[df_filtered['Température (°C)'] > 30]
        if not hot_cities.empty:
            st.warning(f"🔥 **Fortes chaleurs** : {', '.join(hot_cities['Ville'].tolist())} - Hydratation renforcée recommandée")
        
        # Alertes vent
        windy_cities = df_filtered[df_filtered['Vitesse du vent (m/s)'] > 10]
        if not windy_cities.empty:
            st.warning(f"💨 **Vents forts** : {', '.join(windy_cities['Ville'].tolist())} - Prudence pour activités aériennes")
    
    # Recommandations personnalisées
    st.subheader("🎯 Recommandations Personnalisées")
    
    activity_type = st.selectbox(
        "Sélectionnez votre activité prévue :",
        ["Sport intensif", "Promenade familiale", "Activités enfants", "Travail extérieur", "Tourisme/photos"]
    )
    
    # Critères selon l'activité
    if activity_type == "Sport intensif":
        criteria = (df_filtered['AQI'] <= 50) & (df_filtered['Température (°C)'].between(15, 25))
        message = "AQI ≤ 50 et température 15-25°C"
    elif activity_type == "Promenade familiale":
        criteria = (df_filtered['AQI'] <= 100) & (df_filtered['Température (°C)'].between(18, 28))
        message = "AQI ≤ 100 et température 18-28°C"
    elif activity_type == "Activités enfants":
        criteria = (df_filtered['AQI'] <= 50) & (df_filtered['Température (°C)'].between(20, 26))
        message = "AQI ≤ 50 et température 20-26°C (sécurité enfants)"
    elif activity_type == "Travail extérieur":
        criteria = (df_filtered['AQI'] <= 75) & (df_filtered['Vitesse du vent (m/s)'] <= 8)
        message = "AQI ≤ 75 et vent ≤ 8 m/s"
    else:  # Tourisme
        criteria = (df_filtered['AQI'] <= 100) & (df_filtered['Visibilité (m)'] >= 8000)
        message = "AQI ≤ 100 et visibilité ≥ 8km"
    
    suitable_cities = df_filtered[criteria]
    
    if not suitable_cities.empty:
        best_city = suitable_cities.loc[suitable_cities['Indice_Confort'].idxmax()]
        st.success(f"🎯 **Ville recommandée pour {activity_type.lower()}** : **{best_city['Ville']}** (Critères: {message})")
        
        # Détails de la recommandation
        st.info(f"""
        📊 **Conditions détaillées à {best_city['Ville']}** :
        - 🌡️ Température : {best_city['Température (°C)']}°C (ressenti {best_city['Température ressentie (°C)']}°C)
        - 🌬️ AQI : {best_city['AQI']} ({best_city['Qualite_Air']})
        - 💧 Humidité : {best_city['Humidité (%)']}%
        - 💨 Vent : {best_city['Vitesse du vent (m/s)']} m/s
        - ⭐ Indice confort : {best_city['Indice_Confort']:.0f}/100
        """)
    else:
        st.error(f"❌ Aucune ville ne répond aux critères optimaux pour {activity_type.lower()}. Reportez l'activité ou choisissez la ville avec le meilleur indice de confort.")
    
    # ============ EXPORT ET RAPPORTS ============
    st.header("📋 Export et Rapports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Export CSV filtré
        csv_filtered = df_filtered.to_csv(index=False)
        st.download_button(
            label="📄 Télécharger Données Filtrées (CSV)",
            data=csv_filtered,
            file_name=f"meteo_filtered_{date_selectionnee}_{len(villes_selectionnees)}villes.csv",
            mime="text/csv"
        )
    
    with col2:
        # Export rapport complet
        if st.button("📊 Générer Rapport Complet"):
            with st.spinner("Génération du rapport..."):
                # Créer un rapport au format markdown
                rapport = f"""# Rapport Météorologique et Qualité de l'Air
**Date d'analyse :** {date_selectionnee}
**Villes analysées :** {', '.join(villes_selectionnees)}
**Généré le :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Résumé Exécutif
- **Température moyenne :** {df_filtered['Température (°C)'].mean():.1f}°C
- **AQI moyen :** {df_filtered['AQI'].mean():.0f}
- **Ville aux meilleures conditions :** {df_filtered.loc[df_filtered['Indice_Confort'].idxmax(), 'Ville']}
- **Ville la plus polluée :** {df_filtered.loc[df_filtered['AQI'].idxmax(), 'Ville']}

## Statistiques Détaillées
{df_filtered[['Température (°C)', 'AQI', 'Humidité (%)', 'Vitesse du vent (m/s)', 'Indice_Confort']].describe().to_string()}

## Recommandations
- Éviter activités sportives intenses dans les villes avec AQI > 100
- Privilégier les sorties dans les zones à fort indice de confort
- Adapter les activités selon les conditions locales
"""
                
                st.download_button(
                    label="📄 Télécharger Rapport (MD)",
                    data=rapport,
                    file_name=f"rapport_meteo_{date_selectionnee}.md",
                    mime="text/markdown"
                )
    
    with col3:
        # Résumé statistique
        if st.button("📈 Afficher Statistiques"):
            st.subheader("📊 Statistiques Descriptives")
            numeric_columns = ['Température (°C)', 'AQI', 'Humidité (%)', 
                             'Vitesse du vent (m/s)', 'Indice_Confort']
            stats_df = df_filtered[numeric_columns].describe()
            st.dataframe(stats_df.round(2), use_container_width=True)
    
    # ============ DONNÉES BRUTES ============
    with st.expander("📋 Voir les données brutes complètes"):
        st.subheader("🗃️ Dataset Complet")
        # Options d'affichage
        col1, col2 = st.columns(2)
        with col1:
            show_all_columns = st.checkbox("Afficher toutes les colonnes", False)
        with col2:
            sort_by = st.selectbox("Trier par", ['Indice_Confort', 'AQI', 'Température (°C)', 'Ville'])
        
        if show_all_columns:
            display_df = df_filtered.sort_values(sort_by, ascending=False)
        else:
            # Colonnes essentielles uniquement
            essential_cols = ['Ville', 'Température (°C)', 'AQI', 'Humidité (%)', 
                            'Vitesse du vent (m/s)', 'Indice_Confort', 'Condition météo']
            display_df = df_filtered[essential_cols].sort_values(sort_by, ascending=False)
        
        st.dataframe(display_df, use_container_width=True, height=400)
    
    # Footer avec informations
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        🌡️ Application d'Analyse Météorologique & Qualité de l'Air<br>
        Données en temps réel • Analyses prédictives • Recommandations personnalisées<br>
        Développé avec Streamlit & Plotly
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()