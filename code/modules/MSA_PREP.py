#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 13 11:12:51 2021

@author: schaferjw

To run this script:
    python hhfilter.py --i file_in.msa
The .msa file is created using HHMER

"""

import os
from os import listdir
from os.path import isfile, join
import sys
import re
import argparse
import numpy as np
import pandas as pd
import subprocess

"""
file_in = input MSA generated by HMMER
qid     = the number of iterationsof qid threshold the script will loop through, default is 50
row     = limit for % of row that cover the qurey sequence, default = 0.25
column  = limit for the % of columns that contain gaps, default = 0.75

"""
class HHFILTER():
    def __init__(self,file_in, qid=50, row=0.25, column=0.75):
        self.cwd =  os.getcwd()
        self.file_in = file_in
        self.qid = qid
        self.row = row
        self.column = column
        
	#create the initial a2m file for hhfilter
        print('running hhfilter')
        os.system('reformat.pl sto a2m {:} {:}.a2m'.format(self.file_in,self.file_in[:-4]))
        
    def Filter(self):
        
        """
        run hhfilter with increasing values of -qid to create msa's that are smaller and 
        more related to the query sequence.
        """
        os.system('mkdir {:}/{:}'.format(self.cwd,self.file_in[:-4]))
        temp = np.linspace(0,50,num=51)
        qid_list = []
        for i in temp:
            if i < 10:i = str('0{:}'.format(int(i)))
            else: i = str(int(i))
            qid_list.append(i)
        
        for i in qid_list: 
            os.system('hhfilter -i {:}.a2m -o trial.a3m -qid {:}'.format(self.file_in[:-4],i))
            subprocess.check_output('reformat.pl a3m sto trial.a3m {:}/{:}/{:}.sto'.format(self.cwd,self.file_in[:-4],i), shell=True)
            subprocess.check_output('mv trial.a3m {:}/{:}/{:}.a3m'.format(self.cwd,self.file_in[:-4],i), shell=True)
        
    def Data(self,Beg=0,End=0):
        files = [i for i in listdir('{:}/{:}'.format(self.cwd,self.file_in[:-4])) if isfile(join('{:}/{:}'.format(self.cwd,self.file_in[:-4]), i))]
        
        #__________________________________________________________
        for file in files:
            if file[-3:] == 'sto':
                #read in the entire msa, remove top lines and bottom line to isolate sequences
                data = [line.strip() for line in open('{:}/{:}/{:}'.format(self.cwd,self.file_in[:-4],file), 'r')] 
                del data[0:4]
                del data[-1]
                #__________________________________________________________
                
                msa,name=[],[]
                for i in data:  #seperate name and msa data
                    name.append(i[0:34-1]) #NOTE: the sequences should start in column 34, if output is incorrect change 34 to the column the sequence starts on in the .sto file
                    seq = self.Split(i[34:-1])
                    msa.append(seq)
                msa,name,aa = self.Clean_query(msa, name) #aa preserves a.a. positions
                msa,name = self.Remove_rows(msa, name)
                msa,name,aa = self.Remove_columns(msa, name, aa)
                
                #write output to storage files
                self.Output_for_gremlin(msa,name,aa,file,Beg,End)                   
        
        #__________________________________________________________

    def Clean_query(self,msa,name):
        """
        Remove columns that are a space in the query sequence. They aren't useful for coevolutionary analysis'

        """
        df = pd.DataFrame(msa, index=(name))
        df = df[0].str.split('',expand=True)             #seperate all a.a. into there own column
        if df[0][0] == '':
            df = df.drop([0],axis=1)                     #if first column is empty it is deleted
        temp = list(df)
        if df[temp[-1:][0]][0] == '':                    #if the last column is empty delete it
            df = df.drop(temp[-1:][0],axis=1)
        print('msa started at {:} rows and {:} columns'.format(df.shape[0],df.shape[1]))
        #Create list of columns to be deleted and remove them from dataframe
        remove = []
        for i in df.columns:
            if df[i][0] == '-':
                remove.append(i)
        df = df.drop(columns=remove)
        #__________________________________________________________
        aa = list(df)
        name = list(df.index.values)
        msa = df.values.tolist()
        print('msa has been reduced to {:} rows and {:} columns'.format(df.shape[0],df.shape[1]))
        return msa, name, aa

    def Remove_rows(self,msa,name):
        
        """
        Filter sequences that cover less than 25% of the query sequence
        """
        
        # Create list of sequences that have too many gaps and remove them from both msa and name
        msa_red = []
        name_red = []

        for i in range(len(msa)):
            if msa[i].count('-')/len(msa[0]) > self.row:  
                msa_red.append(msa[i])
                name_red.append(name[i])
        for i in msa_red:
            msa.remove(i)
        for i in name_red:
            name.remove(i)
        #__________________________________________________________

        # check to see if filter removed too many sequences or none.
        if len(msa_red) == 0:
            print('All sequences in alignment passed the {:} row gap threshold!'.format(self.row))
        elif len(msa_red) == len(msa):
            print('This gap cutoff has removed all sequences from the msa, choose a higher cutoff.')
        else:
            print('msa has been reduced to {:} rows and {:} columns'.format(len(msa),len(msa[0])))
        return msa,name

    def Remove_columns(self,msa,name,aa):
        """
        columns that are made up of greater than 25% gaps will be excluded 
        """
        # create datafrom with positions as column titles and seq name as index titles
        df = pd.DataFrame(msa,index=(name))      #create initial data frame
        aa = list(range(aa[0],len(aa)+int(aa[0])))
        df.columns = aa
        #__________________________________________________________
        
        #Remove columns 
        freq_all = []
        freq_ = []
        temp = list(df)
        for f in temp:
            freq_.append((df[df[f]=='-'].shape[0]/df[f].count(),f))   #isolate frequency of - in columns
            freq_all.append((df[f].value_counts(normalize=True)))  #all frequencies if needed in columns
        for f in freq_:
            if f[0] > self.column:
                df = df.drop([f[1]],axis=1)
        
        #__________________________________________________________

        print('msa has been reduced to {:} rows and {:} columns'.format(df.shape[0],df.shape[1]))
        name = list(df.index.values)
        msa = df.values.tolist()
        aa = list(df)
 
        return msa, name, aa

    def Output_for_gremlin(self,msa,name,aa,file,Beg,End):
        """
        Save the final version of the msa in a format that gremlin can read: .out
        Save the final version of the msa as a csv file with the positions saved in the first line
        """
        
        df = pd.DataFrame(msa,index=(name),columns=aa)      #create initial data frame
        End = len(list(df)) - End
        df = df.iloc[:,Beg:End]  #trim output if needed beg=10 (delete first 10 positions) end=10 (delete last 10 positions)
        path = self.cwd+'/{:}/{:}.csv'.format(self.file_in[:-4],file[:-4])
        df.to_csv(r'{:}'.format(path))
        os.system('sed "s/,//g" < {:} > {:}.out'.format(path,path[:-4]))
        os.system('sed -i -e "1d" {:}.out'.format(path[:-4]))
        os.system('rm -f {:}.out-e'.format(path[:-4]))

    def Split(self,line): return [char for char in line]