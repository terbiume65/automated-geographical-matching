import streamlit as st
import pandas as pd
import re
import time
from easynmt import EasyNMT
from Levenshtein import distance 
import gc
from io import BytesIO


#Initialization of storage
if 'Status' not in st.session_state:
    st.session_state['Status'] = 'Input'
if 'Dataset' not in st.session_state:
    st.session_state['Dataset'] = None
if 'Output' not in st.session_state:
    st.session_state['Output'] = None


df=st.session_state['Dataset'] 
engine=pd.read_csv("correction.csv",encoding="utf-8-sig")
official=pd.read_csv("official.csv",encoding="utf-8-sig")

def CheckString(s):
    onlyString=True
    for i in range(len(list(s))):
        if type(s[i])!="str":
            onlyString=False
    return onlyString

def CheckEnglish(s):
    isEnglish=True
    isEnglish=bool(re.match("^[a-zA-Z\s\.,-/'()]+$",s))
    return isEnglish

def match(target,engine):
    new=[]
    model = EasyNMT('opus-mt')
    words=list(target)
    pool=engine["Name"].str.lower().values
    for j in range(len(words)):
        target=words[j].lower()
        matched=False
        for k in range(len(pool)):#attempt direct matching
            if target==pool[k]:
                words[j]=engine["ISO1"][k]
                matched=True
        if not matched:#if direct matching fails
            if not CheckEnglish(target):#translate if not English
                target=model.translate(target, target_lang='en')
            distmatrix=[]
            threshold=round(0.50*len(target))
            for m in range(len(pool)):
                distmatrix=distmatrix+[distance(target,pool[m])]
                if min(distmatrix)<=threshold:
                    words[j]=engine["ISO1"][distmatrix.index(min(distmatrix))]
                else:
                    words[j]="Not found"
        
    new=words
    return new

def directmatch(targetlist,searchcol,returncol):
    outputlist=[]
    for i in range(len(targetlist)):
        if targetlist[i] in list(searchcol):
            outputlist=outputlist+[returncol[list(searchcol).index(targetlist[i])]]
        else:
            outputlist=outputlist+["Not found"]
    return outputlist


@st.cache
def convert_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')



st.title("Automation of Geographical Matching")
st.write("This web app takes a dataset with a column of unofficial country names, even with spelling mistakes or in a different language, and return its standardized ISO code (alpha-3, alpha-2, numeric) and its UNDP official name.")
st.header("Input")
file=st.file_uploader('Upload your dataset',type=["csv","xls","xlsx"]) 
submit=st.button("Submit")
if submit==True:
    try:
        if file!=None:
            if file.name.find(".csv")!=-1: #Found .csv extension in file name
                df=pd.read_csv(file)
                st.session_state['Dataset'] = df
                st.session_state['Status'] = 'Settings'
            else: #Other extensions
                df=pd.read_excel(file)
                st.session_state['Dataset'] = df
                st.session_state['Status'] = 'Settings'
    except NameError:
        st.subheader("File not found. Please upload your file above.")
    except ValueError:
        st.subheader("File not found. Please upload your file above.")

if st.session_state['Status'] == 'Settings':
    st.subheader("Your dataset:")
    displaydf=df.astype("str")
    st.table(displaydf)

st.header("Settings")
if st.session_state['Status'] == 'Settings':
    options=list(df.columns)
    st.subheader("Column of country names")
    choice=st.selectbox("Select the column of country names in your dataset",options)
    st.subheader("Output columns (You may select multiple)")
    outcol=st.multiselect("Select your desired output columns",["ISO3166 Alpha-3 (3-letter) Country Code","ISO3166 Alpha-2 (2-letter) Country Code","ISO3166 Numeric Country Code","UNDP Official Name"],"ISO3166 Alpha-3 (3-letter) Country Code")
    
    
    start=st.button("Match")
    message=st.empty()
    progresslabel=st.empty()
    progressbar=st.empty()
    successful=st.empty()
    outputlabel=st.empty()
    outputdf=st.empty()

    if start:
        words=df[choice]
        if CheckString(words)==False:
            for i in range(len(words)):
                try:
                    words[i]=str(words[i])
                except:
                    st.error("The chosen column of your dataset containing country names also contains other data types. Attempt to turn them into string failed. Please check your dataset/chosen column again.")
        results=[]
        n = 8
        batches = [words[i * n:(i + 1) * n] for i in range((len(words) + n - 1) // n )]
        message.info("The column is sliced into "+str(len(batches))+" batches of length "+str(n)+", starting the matching process...")
        
        for i in range(len(batches)):
            
            progresslabel.write("Matching of item "+str(i*n+1)+" to "+str((i+1)*n)+"...")
            results=results+match(batches[i],engine)
            progressbar.progress(int((i/(len(batches)+1))*100))

            gc.collect()
        
        #Output results
        if "ISO3166 Alpha-3 (3-letter) Country Code" in outcol:
            df["ISO alpha-3"]=results
        if "ISO3166 Alpha-2 (2-letter) Country Code" in outcol:
            df["ISO alpha-2"]=directmatch(results,official["ISO3"],official["ISO2"])
        if "ISO3166 Numeric Country Code" in outcol:
            df["ISO numeric"]=directmatch(results,official["ISO3"],official["N"])
            df["ISO numeric"]=df["ISO numeric"].astype("str")
        if "UNDP Official Name" in outcol:
            df["UNDP Official Name"]=directmatch(results,official["ISO3"],official["UNDPName"])


        progressbar.progress(100)
        successful.success("Matching complete")
        st.session_state['Output']=df
        outputlabel.subheader("Output:")
        outputdf.dataframe(st.session_state['Output'])

    if st.session_state['Output'] is not None:
        outputlabel.subheader("Output:")

        outputdf.dataframe(st.session_state['Output'])
        col1, col2 = st.columns(2)
        csv=convert_csv(st.session_state['Output'])
        st.download_button(
        label="Download as CSV",
        data=csv,
        mime='text/csv',)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state['Output'].to_excel(writer,index=False, sheet_name='Sheet1')
            writer.save()
        
        st.download_button(label="Download as Excel",file_name="output.xlsx",data=buffer,)

        
        

    
        






