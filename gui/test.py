from tkinter import Tk, Label, Button, Entry
from matplotlib import pyplot as plt
from tkinter import filedialog
import numpy as np
from scipy.optimize import curve_fit




def Plotwidth(Data,DeltaNu):
    xMin=np.argmin(data[:]-center-DeltaNu)
    xMax=np.argmin(data[:]-center+DeltaNu)
    xx=Data[xMin:xMax]


    return xx

def Lorentzian(x,h,a,x0,d,c):
    return h*((a**2/4)/((a**2/4) + (x - x0)**2))+d+c*x



class MyFirstGUI:
    def __init__(self, master):
        self.master = master
        master.title("A simple GUI")

        self.label = Label(master, text="This is our first GUI!")
        self.label.pack()

        self.greet_button = Button(master, text="choose file", command=self.greet)
        self.greet_button.pack()

        self.close_button = Button(master, text="Close", command=master.quit)
        self.close_button.pack()

        self.entry = Entry(master)
        self.entry.pack()

        self.Linewidth_button = Button(master, text="Linewidth", command=self.close_button)
        self.Linewidth_button.pack()
        self.x = []
        self.y = []
        self.center = 0



    def readlinewidth(self):

        self.string = self.Linewidth_button.get()
        print(self.string)
        popt, pcov = curve_fit(Lorentzian, self.x, self.y)


    def greet(self):
        file_path = filedialog.askopenfilename()
        Data = np.genfromtxt(file_path, delimiter=',')
        self.x = Data[:, 0]
        self.y = Data[:, 2]
        fig, axes = plt.subplots(1, 1, figsize=(5, 5))
        axes.plot(self.x, self.y)

root = Tk()
my_gui = MyFirstGUI(root)
root.mainloop()

