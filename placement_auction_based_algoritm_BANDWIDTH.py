# Importing EdgeSimPy components
from edge_sim_py import *

# Importing Python libraries
import os
import random
import msgpack
import pandas as pd
import itertools
import socket
import subprocess
import logging
import math

#services_data = {}

# Criando os serviços e definindo a demanda de CPU e RAM para cada um
#for service_data in services_data:
#    Service(**service_data)

# Implementação do algoritmo de leilão para placement
def my_algorithm(parameters):
    # Criando um dicionário para armazenar as propostas dos servidores de borda
    server_proposals = {}

    # Iterando sobre todos os serviços que não estão sendo provisionados atualmente
    for service_id in range(1, 7):
        service = None
        for s in Service.all():
            if s.id == service_id:
                service = s
                break

        if service is None:
            continue

        if service.server is None and not service.being_provisioned:
            # Iterando sobre todos os servidores de borda disponíveis
            for edge_server in EdgeServer.all():
                # Encontrar o network_switch do edge_server ativo
                network_switch = edge_server.network_switch

                # Iterando sobre todos os links de rede
                for network_link in NetworkLink.all():
                    # Verificando se o servidor de borda tem recursos suficientes para hospedar o serviço
                    if edge_server.has_capacity_to_host(service=service):
                        # Verificando se o network_switch está presente nos nós da network_link
                        if network_switch == network_link.nodes[0]:
                            # Calculando a pontuação do servidor de borda com base na fórmula fornecida
                            bandwidth = network_link.bandwidth - network_link.bandwidth_demand
                            #print(network_switch,network_link.nodes,network_link.bandwidth_demand)
                            cpu_free = edge_server.cpu - edge_server.cpu_demand
                            memory_free = (edge_server.memory - edge_server.memory_demand) / 1024
                            score = abs(math.log10(bandwidth)) + abs(math.log10(memory_free)) + abs(
                                math.log10(cpu_free))
                            # Armazenando a proposta do servidor de borda no dicionário de propostas
                            server_proposals[edge_server.id] = {'score': score, 'service': service}

    # Verificando se há pelo menos uma proposta válida
    if len(server_proposals) > 0:
        # Determinando o servidor vencedor com base na maior pontuação
        winning_server_id = max(server_proposals, key=lambda k: server_proposals[k]['score'])
        winning_server = None
        for edge_server in EdgeServer.all():
            if edge_server.id == winning_server_id:
                winning_server = edge_server
                break

        # Provisionando o serviço no servidor vencedor
        if winning_server:
            service = server_proposals[winning_server_id]['service']
            service.provision(target_server=winning_server)


#Executando a Simulação

#Como estamos criando um algoritmo de placement, devemos instruir o EdgeSimPy que ele precisa continuar a simulação até que 
#todos os serviços estejam provisionados dentro da infraestrutura.

#Para isso, vamos criar uma função simples que será usada como critério de parada da simulação. 
#O #EdgeSimPy executará essa função no final de cada passo de tempo, parando a simulação assim que ela retornar True.
# Definindo a variável global current_time para rastrear o tempo simulado
current_time = 0

def stopping_criterion(model: object):
    # Definição de uma variável que nos ajudará a contar o número de serviços provisionados com sucesso na infraestrutura
    provisioned_services = 0
    
    global current_time  # Definindo current_time como uma variável global para ser acessada e modificada dentro da função
    
    # Iteração sobre a lista de serviços para contar o número de serviços fornecidos na infraestrutura
    for service in Service.all():

        # Inicialmente, os serviços não são hospedados por nenhum servidor (ou seja, seu atributo "server" é None).
        # Quando esse valor muda, sabemos que ele foi provisionado com sucesso dentro de um servidor de borda.
        if service.server != None:
            provisioned_services += 1
    
    # Como o EdgeSimPy interromperá a simulação sempre que esta função retornar True, sua saída será uma expressão booleana
    # que verifica se o número de serviços provisionados é igual ao número de serviços gerados na nossa simulação
    # Retorna True se todos os serviços estiverem provisionados e o tempo total da simulação for pelo menos 90 segundos (90 ticks)
   # Incrementando o tempo simulado em 1 segundo (tick)
    current_time += 1
    
    # Retorna True se todos os serviços estiverem provisionados e o tempo total da simulação for pelo menos 90 segundos (90 ticks)
    return provisioned_services == Service.count() and current_time >= 1440

#Depois de termos o nosso critério de paragem, podemos finalmente executar a nossa simulação criando uma instância da classe Simulator, 
#carregando um conjunto de dados e chamando o método run_model().

# Criar um objeto Simulador
simulator = Simulator(
    tick_duration=1,
    tick_unit="minutes",
    stopping_criterion=stopping_criterion,
    resource_management_algorithm=my_algorithm,
)

# Carregar um conjunto de dados de amostra (JSON) do GitHub
simulator.initialize(input_file='sample_dataset2_U90E5f.json')

# Executando a Simulação
simulator.run_model()

# Verificação do resultado da placement
for service in Service.all():
    print(f"{service}. Host: {service.server}")

# Gathering the list of msgpack files in the current directory
logs_directory = f"{os.getcwd()}/logs"
dataset_files = [file for file in os.listdir(logs_directory) if ".msgpack" in file]

# Reading msgpack files found
datasets = {}
for file in dataset_files:
    with open(f"logs/{file}", "rb") as data_file:
        datasets[file.replace(".msgpack", "")] = pd.DataFrame(msgpack.unpackb(data_file.read(), strict_map_key=False))
datasets["EdgeServer"]
# Defining the data frame columns that will be exhibited
properties = ['Coordinates', 'CPU Demand', 'RAM Demand', 'Disk Demand', 'Services']
columns = ['Time Step', 'Instance ID'] + properties

dataframe = datasets["EdgeServer"].filter(items=columns)
dataframe

def custom_collect_method(self) -> dict:
    temperature = random.randint(10, 50)  # Generating a random integer between 10 and 50 representing the switch's temperature
    metrics = {
        "Instance ID": self.id,
        "Power Consumption": self.get_power_consumption(),
        "Temperature": temperature,
    }
    return metrics

# Overriding the NetworkSwitch's collect() method
NetworkSwitch.collect = custom_collect_method

# Creating a Pandas data frame with the network switch logs
logs = pd.DataFrame(simulator.agent_metrics["NetworkSwitch"])
logs