import csv
from capsulae import settings
import os
#------------------------
# FRAMINGHAM
#------------------------
def framingham(edad, sexo, diabetes, fumador, tension, colesterol, region):
    
    framingham = 0
      
    if (edad >=65 and edad <= 74) :
        age = 1
    if (edad >= 55 and edad <= 64):
        age = 2
    if (edad >= 45 and edad <= 54):
        age = 3
    if (edad >= 35 and edad <= 44):
        age = 4
    if (edad >=75):
        age = 0
    if (edad <= 34):
        age = 0


    # Valor fuera del rango de 35 - 74 años 
 
    if age == 0:
        return  0
   
    #hombres
   
    if (sexo == "H" and age == 1 and diabetes == False and fumador == False):
        framingham = leertabla(tension, colesterol, 1, region)
    if (sexo == "H" and age == 2 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 2, region)
    if (sexo == "H" and age == 3 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 3, region)
    if (sexo == "H" and age == 4 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 4, region)
   
    #hombres fumadores
   
    if (sexo == "H" and age == 1 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 5, region)
    if (sexo == "H" and age == 2 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 6, region)
    if (sexo == "H" and age == 3 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 7, region)
    if (sexo == "H" and age == 4 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 8, region)
    
    #hombres con diabetes
   
    if (sexo == "H" and age == 1 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 9, region)
    if (sexo == "H" and age == 2 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 10, region)
    if (sexo == "H" and age == 3 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 11, region)
    if (sexo == "H" and age == 4 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 12, region)
  
    #hombres con dabietes y fumadores
   
    if (sexo == "H" and age == 1 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 13, region)
    if (sexo == "H" and age == 2 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 14, region)
    if (sexo == "H" and age == 3 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 15, region)
    if (sexo == "H" and age == 4 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 16, region)
   
    #mujeres

    if (sexo == "M" and age == 1 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 17, region)
    if (sexo == "M" and age == 2 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 18, region)
    if (sexo == "M" and age == 3 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 19, region)
    if (sexo == "M" and age == 4 and  diabetes == False and fumador == False):
        framingham = leertabla( tension, colesterol, 20, region)
   
    #mujeres fumadoras
   
    if (sexo == "M" and age == 1 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 21, region)
    if (sexo == "M" and age == 2 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 22, region)
    if (sexo == "M" and age == 3 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 23, region)
    if (sexo == "M" and age == 4 and  diabetes == False and fumador == True):
        framingham = leertabla( tension, colesterol, 24, region)
   
    #mujeres con diabetes
   
    if (sexo == "M" and age == 1 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 25, region)
    if (sexo == "M" and age == 2 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 26, region)
    if (sexo == "M" and age == 3 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 27, region)
    if (sexo == "M" and age == 4 and  diabetes == True and fumador == False):
        framingham = leertabla( tension, colesterol, 28, region)
    
    #mujeres con diabetes y fumadoras
   
    if (sexo == "M" and age == 1 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 29, region)
    if (sexo == "M" and age == 2 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 30, region)
    if (sexo == "M" and age == 3 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 31, region)
    if (sexo == "M" and age == 4 and  diabetes == True and fumador == True):
        framingham = leertabla( tension, colesterol, 32, region)
    
    
    
    return framingham

#lee la tabla de Framinghan correspondiente
def leertabla(tension,colesterol, tabla, region):
    posicion = 0
    valor = 0
    # Niveles de colesterol 
    if colesterol <= 159:
        col = 0
    if (colesterol >= 160 and colesterol <= 199):
        col = 1
    if (colesterol >= 200 and colesterol <= 239):
        col = 2
    if (colesterol >= 240 and colesterol <= 279):
        col = 3
    if (colesterol >= 280):
        col = 4
    
    # Presión Arterial

    if (tension >= 160):
        if col == 0:
            posicion = 0
        if col == 1:
            posicion = 1
        if col == 2:  
            posicion = 2
        if col == 3:  
            posicion = 3
        if col == 4:  
            posicion = 4
     
    if (tension >= 140 and tension <= 159):
        if col == 0:
            posicion = 5
        if col == 1:
            posicion = 6
        if col == 2:  
            posicion = 7
        if col == 3:  
            posicion = 8
        if col == 4:  
            posicion = 9


    if (tension >= 130 and tension <= 139):
        if col == 0:
            posicion = 10
        if col == 1:
            posicion = 11
        if col == 2:  
            posicion = 12
        if col == 3:  
            posicion = 13
        if col == 4:  
            posicion = 14
    
    if (tension >= 120 and tension <= 129):
        if col == 0:
            posicion = 15
        if col == 1:
            posicion = 16
        if col == 2:  
            posicion = 17
        if col == 3:  
            posicion = 18
        if col == 4:  
            posicion = 19

    if (tension < 120):
        if col == 0:
            posicion = 20
        if col == 1:
            posicion = 21
        if col == 2:  
            posicion = 22
        if col == 3:  
            posicion = 23
        if col == 4:  
            posicion = 24
    
    #url = "f_tabla"+str(tabla)+str(region)+".csv"
    url = "f_tabla"+str(tabla)+str(region)+".csv"
    path = os.path.join(settings.BASE_DIR, 'media', url)
    if (os.path.exists(path)):
        with open(path) as File:  
            reader = csv.reader(File, delimiter=',')
            for row in reader:
                print(row)
            valor = row[posicion]
    return valor


 
