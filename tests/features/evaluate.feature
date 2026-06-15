# BDD — Scénarios d'évaluation DMN
# Langage : Gherkin / pytest-bdd

Feature: Évaluation de tables de décision DMN

  Background:
    Given l'API DMN est démarrée

  Scenario: Hit Policy FIRST — première règle matchante
    Given une table "EligibiliteCredit" avec hit policy "FIRST"
    And une colonne input "age" de type "number"
    And une colonne output "decision" de type "text"
    And une règle avec condition "age >= 18" et output "decision = ACCEPTE"
    And une règle avec condition "age < 18" et output "decision = REFUSE"
    When j'évalue avec "age = 25"
    Then le résultat est "decision = ACCEPTE"

  Scenario: Hit Policy FIRST — aucune règle ne matche
    Given une table "TestVide" avec hit policy "FIRST"
    And une colonne input "score" de type "number"
    And une colonne output "niveau" de type "text"
    And une règle avec condition "score > 100" et output "niveau = EXPERT"
    When j'évalue avec "score = 50"
    Then le résultat est null

  Scenario: Hit Policy COLLECT SUM — somme des scores
    Given une table "ScoringRisque" avec hit policy "COLLECT SUM"
    And une colonne input "age" de type "number"
    And une colonne input "revenu" de type "number"
    And une colonne output "score" de type "number"
    And une règle avec condition "age >= 25" et output "score = 10"
    And une règle avec condition "revenu >= 3000" et output "score = 20"
    When j'évalue avec "age = 30, revenu = 4000"
    Then le score total est "30"

  Scenario: Validation — colonne input manquante
    Given une table "TestValidation" avec hit policy "FIRST"
    And une colonne input "age" de type "number"
    And une colonne output "decision" de type "text"
    When j'évalue sans fournir "age"
    Then l'API retourne une erreur 422
