# Personalized Study Guide
Welcome to your personalized study guide, designed to help you overcome your weaknesses in specific topics. This guide will walk you through explanations, worked examples, and practice questions to improve your understanding and mastery of TCP/UDP reliability, packet switching, and linear equations isolation.

## TCP/UDP Reliability
TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) are two fundamental protocols in computer networking. The main difference between them lies in their reliability. 

### Concept Explanation
Think of TCP as a phone call and UDP as sending a postcard. When you make a phone call, you expect the other person to answer, and if they don't, you try again. Similarly, TCP ensures that data is delivered reliably by establishing a connection, breaking data into packets, assigning sequence numbers, and retransmitting lost packets. On the other hand, UDP is like sending a postcard; you send it, but you're not sure if it will arrive, and you don't try to resend it if it doesn't.

### Step-by-Step Solved Problem
**Problem:** Describe the steps involved in ensuring reliability in TCP.
1. **Establish Connection:** The sender and receiver establish a connection through a handshake process.
2. **Sequence Numbering:** Each packet of data is assigned a sequence number.
3. **Acknowledgment:** The receiver sends an acknowledgment (ACK) for the packets received.
4. **Retransmission:** If a packet is lost, the sender retransmits it upon not receiving an ACK within a certain time frame.
5. **Connection Termination:** The connection is terminated when all data has been successfully transmitted and acknowledged.

### Practice Question
What is the primary method used by TCP to ensure that packets are delivered in the correct order?
**Expected Answer:** TCP uses sequence numbers to ensure that packets are delivered in the correct order.

## Packet Switching
Packet switching is a method of transmitting data over a network by breaking it into small packets. 

### Concept Explanation
Imagine you're sending a large package across the country. Instead of sending the whole package at once, you break it into smaller boxes, label each box with the recipient's address and a sequence number, and send them through different routes. This is similar to packet switching, where data is broken into packets, each packet is given a header with addressing information, and they are sent independently through the network.

### Step-by-Step Solved Problem
**Problem:** Explain the process of packet switching.
1. **Data Segmentation:** The data to be sent is broken into smaller segments or packets.
2. **Header Addition:** A header is added to each packet containing source and destination addresses, sequence numbers, and other control data.
3. **Routing:** Each packet is routed independently through the network to the destination.
4. **Reassembly:** At the receiving end, the packets are reassembled into the original data based on the sequence numbers.

### Practice Question
What happens to packets in a packet-switched network if the best path to the destination changes during transmission?
**Expected Answer:** Each packet will be routed through the new best path, which may result in packets arriving out of order.

## Linear Equations Isolation
Linear equations are equations in which the highest power of the variable(s) is 1. Isolating the variable means solving for the variable.

### Concept Explanation
Consider a balance scale where you have weights on both sides. To isolate a weight (or variable), you need to ensure that it's the only weight on its side. Similarly, in linear equations, you isolate the variable by performing operations that move all other terms to the opposite side of the equation, ensuring the variable is alone on one side.

### Step-by-Step Solved Problem
**Problem:** Solve for x in the equation 2x + 5 = 11.
1. **Subtract 5 from both sides:** 2x = 11 - 5, so 2x = 6.
2. **Divide both sides by 2:** x = 6 / 2, so x = 3.

### Practice Question
Solve for y in the equation y - 3 = 7.
**Expected Answer:** y = 10.