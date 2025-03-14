-- 1. Vérifier que toutes les villes ont été importées
SELECT *
FROM villes;
-- 2. Compter le nombre de villes
SELECT COUNT(*) AS nombre_villes
FROM villes;
-- 3. Vérifier les données météo pour chaque ville
SELECT v.nom AS ville,
    m.date_releve,
    ROUND(m.temperature::numeric, 2) AS temperature_celsius,
    ROUND(m.temperature_ressentie::numeric, 2) AS temperature_ressentie,
    m.humidite AS pourcentage_humidite,
    m.description_meteo
FROM meteo m
    JOIN villes v ON m.ville_id = v.id
ORDER BY v.nom,
    m.date_releve DESC;
-- 4. Vérifier les données de qualité d'air
SELECT v.nom AS ville,
    qa.date_releve,
    qa.aqi AS indice_qualite_air,
    qa.polluant_dominant,
    qa.pm25,
    qa.pm10,
    qa.o3 AS ozone,
    qa.no2 AS dioxyde_azote
FROM qualite_air qa
    JOIN villes v ON qa.ville_id = v.id
ORDER BY v.nom,
    qa.date_releve DESC;
-- 5. Vérifier les prévisions de qualité d'air pour les prochains jours
SELECT v.nom AS ville,
    pqa.date_prevision,
    pqa.type_polluant,
    pqa.valeur_moyenne,
    pqa.valeur_min,
    pqa.valeur_max
FROM previsions_qualite_air pqa
    JOIN villes v ON pqa.ville_id = v.id
WHERE pqa.date_prevision >= CURRENT_DATE
ORDER BY v.nom,
    pqa.date_prevision,
    pqa.type_polluant;
-- 6. Résumé de la qualité d'air par ville (classement)
SELECT v.nom AS ville,
    qa.aqi AS indice_qualite_air,
    CASE
        WHEN qa.aqi <= 50 THEN 'Bon'
        WHEN qa.aqi <= 100 THEN 'Modéré'
        WHEN qa.aqi <= 150 THEN 'Mauvais pour groupes sensibles'
        WHEN qa.aqi <= 200 THEN 'Mauvais'
        WHEN qa.aqi <= 300 THEN 'Très mauvais'
        ELSE 'Dangereux'
    END AS qualification
FROM qualite_air qa
    JOIN villes v ON qa.ville_id = v.id
ORDER BY qa.aqi;
-- 7. Contrôle d'intégrité des données
-- Vérifier s'il manque des données météo pour certaines villes
SELECT v.nom AS ville,
    CASE
        WHEN m.id IS NULL THEN 'Manquant'
        ELSE 'Présent'
    END AS donnees_meteo,
    CASE
        WHEN qa.id IS NULL THEN 'Manquant'
        ELSE 'Présent'
    END AS donnees_qualite_air
FROM villes v
    LEFT JOIN meteo m ON v.id = m.ville_id
    LEFT JOIN qualite_air qa ON v.id = qa.ville_id
GROUP BY v.nom,
    donnees_meteo,
    donnees_qualite_air;
-- 8. Corrélation température/qualité d'air
SELECT v.nom AS ville,
    ROUND(AVG(m.temperature)::numeric, 1) AS temperature_moyenne,
    AVG(qa.aqi) AS aqi_moyen,
    ROUND(CORR(m.temperature, qa.aqi)::numeric, 2) AS correlation
FROM villes v
    JOIN meteo m ON v.id = m.ville_id
    JOIN qualite_air qa ON v.id = qa.ville_id
GROUP BY v.nom;
-- 9. Vérifier la ville avec la meilleure qualité d'air
SELECT v.nom AS ville,
    qa.aqi AS indice_qualite_air
FROM qualite_air qa
    JOIN villes v ON qa.ville_id = v.id
ORDER BY qa.aqi ASC
LIMIT 5;
-- 10. Vérifier la ville avec la moins bonne qualité d'air
SELECT v.nom AS ville,
    qa.aqi AS indice_qualite_air
FROM qualite_air qa
    JOIN villes v ON qa.ville_id = v.id
ORDER BY qa.aqi DESC
LIMIT 5;