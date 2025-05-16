# -*- coding: utf-8 -*-
"""
Optimized SIP listener for OVH using pjsua2
"""
import os  # pour accéder aux variables d'environnement
import sys  # pour gérer la sortie du programme
import signal  # pour intercepter les signaux système (CTRL+C, etc.)
import threading  # pour maintenir la boucle principale en vie
import time  # pour pauses entre envois SIP
import logging  # pour journalisation et débogage
from dotenv import load_dotenv  # pour charger les variables depuis .env
import pjsua2 as pj  # bibliothèque PJSIP (pjsua2) pour SIP et RTP

# Configuration du logger pour afficher les messages de debug et plus
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("sip_listener")  # logger principal du module

# Chargement des paramètres SIP depuis .env
load_dotenv()
SIP_USERNAME = os.getenv("SIP_USERNAME")  # identifiant utilisateur SIP
SIP_PASSWORD = os.getenv("SIP_PASSWORD", "")  # mot de passe SIP (optionnel)
SIP_SERVER = os.getenv("SIP_SERVER")  # domaine ou IP du serveur SIP
SIP_PORT = int(os.getenv("SIP_PORT", "5060"))  # port UDP pour SIP
PUBLIC_HOST = os.getenv("PUBLIC_HOST")  # IP publique/FQDN pour SDP
logger.debug(f"Config loaded: username={SIP_USERNAME}, server={SIP_SERVER}, port={SIP_PORT}, public_host={PUBLIC_HOST}")

ep = None  # variable globale pour stocker l'endpoint pjsua2

class MyCallCallback(pj.CallCallback):
    def __init__(self, call=None):
        super().__init__(call)
        self.tone_gen = pj.ToneGenerator()  # générateur de silence pour le flux audio
        logger.debug(f"CallCallback créé pour l'appel ID={self.call.getId()}")

    def onState(self, prm: pj.OnCallStateParam):
        # appelé à chaque changement d'état de l'appel (ex: CONFIRMED)
        info = self.call.getInfo()
        logger.info(f"Appel {self.call.getId()} état: {info.stateText}")
        # dès que la session est confirmée, on transmet du silence en RTP
        if info.state == pj.PJSIP_INV_STATE_CONFIRMED:
            logger.debug(f"Appel {self.call.getId()} confirmé: début du silence RTP")
            self.tone_gen.createChannel(0, 0)  # fréquence 0 Hz, gain 0 dB = silence
            self.tone_gen.startTransmit(self.call)  # attache le silence au flux média

    def onMediaState(self, prm: pj.OnCallMediaStateParam):
        # appelé lors d'un changement d'état média (ex: codec choisi)
        logger.debug(f"Media state changé pour appel {self.call.getId()}: {prm}")

class MyAccountCallback(pj.AccountCallback):
    def __init__(self, account=None):
        super().__init__(account)
        self.logger = logging.getLogger("AccountCallback")  # logger dédié au compte

    def onIncomingCall(self, prm: pj.OnIncomingCallParam):
        # gestion des appels entrants (INVITE)
        self.logger.info(f"Appel entrant reçu: ID={prm.callId}")
        call = pj.Call(self.account, prm.callId)  # instancie l'appel
        call_cb = MyCallCallback(call)  # crée le callback pour cet appel
        call.setCallback(call_cb)  # associe le callback à l'appel
        # envoie 180 Ringing pour indiquer la sonnerie
        self.logger.debug(f"Envoi 180 Ringing pour appel {call.getId()}")
        call.answer(180, "Ringing")
        time.sleep(1)  # courte pause avant la confirmation
        # envoie 200 OK pour établir la session
        self.logger.debug(f"Envoi 200 OK pour appel {call.getId()}")
        call.answer(200, "OK")

def init_endpoint() -> pj.Endpoint:
    # initialisation de la librairie PJSIP et création du transport UDP
    logger.info(f"Initialisation de l'endpoint sur le port {SIP_PORT}")
    endpoint = pj.Endpoint()
    endpoint.libCreate()  # prépare la librairie
    ua_cfg = pj.EpConfig()
    ua_cfg.uaConfig.userAgent = "OVH-pjsua2/1.0"  # identifiant custom pour OVH
    ua_cfg.uaConfig.maxCalls = 4  # nombre max d'appels simultanés
    endpoint.libInit(ua_cfg)  # applique la configuration
    tp_cfg = pj.TransportConfig()
    tp_cfg.port = SIP_PORT  # port d'écoute UDP
    tp_cfg.setQosType(pj.PjQosType.PJ_QOS_SIGNALING)  # QoS pour signalisation
    tp_cfg.enableKeepAlive = True  # envoie périodique de keep-alive NAT
    endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)  # création du transport
    endpoint.libStart()  # démarre le thread PJSIP
    logger.info(f"Endpoint démarré sur 0.0.0.0:{SIP_PORT}")
    return endpoint

def create_account(endpoint: pj.Endpoint) -> pj.Account:
    # création et enregistrement du compte SIP
    logger.info("Création du compte SIP et enregistrement")
    acc_cfg = pj.AccountConfig()
    acc_cfg.idUri = f"sip:{SIP_USERNAME}@{SIP_SERVER}"  # URI de l'utilisateur
    acc_cfg.regConfig.registrarUri = f"sip:{SIP_SERVER}:{SIP_PORT}"  # registrar
    acc_cfg.sipConfig.authCreds.append(
        pj.AuthCredInfo("digest", "*", SIP_USERNAME, 0, SIP_PASSWORD)
    )  # ajoute les infos d'authentification Digest
    acc_cfg.regConfig.timeoutSec = 300  # rafraîchissement auto toutes les 5 min
    account = pj.Account()
    account.create(acc_cfg)  # enregistre le compte auprès du serveur
    account.setCallback(MyAccountCallback(account))  # associe le callback du compte
    return account

def shutdown(signum, frame):
    # gestion d'arrêt propre à la réception d'un signal
    global ep
    logger.warning(f"Signal d'arrêt {signum} reçu: destruction de l'endpoint")
    if ep:
        try:
            ep.libDestroy()  # nettoie et ferme la librairie PJSIP
            logger.info("Endpoint détruit avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la destruction: {e}")
    sys.exit(0)  # quitte le programme

if __name__ == "__main__":
    # associe les signaux SIGINT et SIGTERM à la fonction shutdown
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # initialise l'endpoint et crée le compte SIP
    ep = init_endpoint()
    acc = create_account(ep)
    # boucle principale bloquante pour garder le service actif
    logger.info("Prêt à recevoir des appels !")
    threading.Event().wait()  # attend indéfiniment
