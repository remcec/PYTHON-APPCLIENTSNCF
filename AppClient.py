from flask import Flask, render_template, request
import requests
from zeep import Client
from datetime import datetime

# Valeur du token pour accéder a l'API SNCF et lien vers les API SOAP et REST
TOKENSNCF = 'f1196796-7240-473a-95b2-b350b176c420'
APISOAPSNCF = 'https://java-soap-sncf-remi.herokuapp.com/services/CalculDistance?wsdl'
APIRESTSNCF = 'https://python-rest-sncf-remi.herokuapp.com/API/CalculPrix'

AppClient = Flask(__name__)

@AppClient.route('/')
def index():
    return render_template('index.html')

# On accepte la méthode POST seulement pour accéder a ce lien car on va récupérer les informations du client pour rechercher les trains depuis un formulaire
@AppClient.route('/RechercheTrains', methods=['POST'])
def rechercherTrains():
    urlGare = 'http://data.sncf.com/api/records/1.0/search/'
    etaterreur = 0
    tableauVoyage = []

    # Gestion d'erreur de récupération de code gare et coordonnées dans le cas ou la ville n'existe pas ou n'a pas de gare
    try:
        # On récupère les valeurs générales de la gare de départ avec l'API SNCF
        infoGareDep = requests.get(urlGare, params = {'dataset' : 'referentiel-gares-voyageurs', 'q':request.form['villedepart']}).json()

        # On récupère des informations en particulier sur la gare de départ
        # wgs_84 contient les coordonnés de latitude et longitude de la gare
        coordGareDep = infoGareDep['records'][0]['fields']['wgs_84']
        #pltf_uic_code contient un numéro qui identifie la gare
        codeGareDep = str(infoGareDep['records'][0]['fields']['pltf_uic_code'])

    # Ce qu'on fait si il y a une erreur
    except:
        etaterreur = 1
        distanceKm = 'DISTANCE INCALCULABLE '
        devise = request.form['devise']
        erreur = 'Pas de voyage disponible car la ville '+request.form['villedepart']+' est incorrecte ou ne possède pas de gare'
        tableauVoyage.append(erreur)
        prixTotal = 'PRIX INCALCULABLE '

    # Même principe qu'au dessus mais pour la gare d'arrivée cette fois
    try:
        # Même principe qu'au dessus mais pour la gare d'arrivée cette fois
        infoGareAr = requests.get(urlGare, params = {'dataset' : 'referentiel-gares-voyageurs', 'q':request.form['villearrive']}).json()

        coordGareAr = infoGareAr['records'][0]['fields']['wgs_84']
        codeGareAr = str(infoGareAr['records'][0]['fields']['pltf_uic_code'])
    except:
        etaterreur = 1
        distanceKm = 'DISTANCE INCALCULABLE '
        devise = request.form['devise']
        erreur = 'Pas de voyage disponible car la ville '+request.form['villearrive']+' est incorrecte ou ne possède pas de gare'
        tableauVoyage.append(erreur)
        prixTotal = 'PRIX INCALCULABLE '

    # Si on a pas eu de problème pour récupérer les informations des gares
    if(etaterreur==0):
        # Calcul de la distance entre les gare en envoyant les coordonnées à l'API SOAP
        distanceKm = Client(APISOAPSNCF).service.calcDistance(coordGareDep[0], coordGareDep[1], coordGareAr[0], coordGareAr[1])

        # Récupération de la devise choisie depuis le formulaire Client
        devise = request.form['devise']

        # Calcul du prixtotal en envoyant la distance en km et la devise choisi à l'API REST
        prixTotal = requests.get(APIRESTSNCF+'/distance/'+distanceKm+'/devise/'+devise).json()['totalfinal']

        # Récupération de la date choisie depuis le formulaire Client
        dateVoyage = datetime.strptime(request.form['datedepart'], '%Y-%m-%d')

        # On récupère les voyages correspondant a la demande du client avec l'API SNCF
        voyagePrevu = requests.get('https://api.sncf.com/v1/coverage/sncf/journeys?', params = {'from':'stop_area:OCE:SA:'+codeGareDep, 'to':'stop_area:OCE:SA:'+codeGareAr, 'min_nb_journeys': 3, 'datetime': dateVoyage}, auth=(TOKENSNCF, '')).json()

        # On vérifie qu'il y'a au moins un voyage de disponible sinon on rentre un message d'erreur dans le tableau
        try:
            voyagePrevu['journeys']
        except:
            etaterreur = 1
            erreur = 'Pas de voyage disponible pour cette date'
            tableauVoyage.append(erreur)

        # Si on a obtenu au moins un voyage
        if(etaterreur==0):
            for index in range(0,len(voyagePrevu['journeys'])):
                tableauVoyage.append(datetime.strptime(voyagePrevu['journeys'][index]['departure_date_time'].replace('T',''),'%Y%m%d%H%M%S'))
            tableauVoyage.reverse()
        
    # On retourne la page html indiqué avec les différentes variables à afficher dynamiquement
    return render_template('RechercheTrains.html', villeDepart=request.form['villedepart'], villeArrive=request.form['villearrive'], distance=distanceKm, laDevise=devise, prix=prixTotal, voyages=tableauVoyage)