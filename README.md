### Petrache Gabriela Andreea
## Implementare Switch


* Cand switch-ul primeste un pachet, verifica tipul interfetei de pe care a venit, daca este de tip access, se adauga in tabela de vlan a switch-ului vlan-ul interfetei de pe care a venit, daca este de tip trunk, se adauga vlan_id-ul. Daca pachetul contine un tag de vlan, se scoate tag-ul si se miscoreaza lungimea pachetului. 
* Se verifica daca mac-ul destinatiei este de tip unicast sau broadcast. Daca este unicast, se verifica tabela de mac a switch-ului, iar daca se gaseste, se trimite pachetul pe interfata, dar se adauga tag daca interfata este de tip trunk.
* Daca mac-ul nu se afla in tabela de vlan-uri, se cauta pe interfetele vecine. Daca este de tip access, se verifica daca interfata vecina este in acelasi vlan cu host-ul care a trimis pachetul. Daca este de tip trunk, se trimite pachetul pe toate interfetele de tip trunk, dar se adauga tag daca interfata este de tip trunk.
* Daca mac-ul este de tip broadcast, se trimite pachetul pe toate interfetele de tip access din acelasi vlan, si pe toate interfetele de tip trunk, cu tag-ul corespunzator.
