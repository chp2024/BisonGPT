import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState, useEffect, useRef } from "react";
import {
  useChatInteract,
  useChatMessages,
  IStep,
} from "@chainlit/react-client";

// Avatar image URLs (or local assets)
import userAvatar from '../assets/user_avatar.jpg';
import botAvatar from '../assets/Howard_Bison_logo.png';

export function Playground() {
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const { sendMessage } = useChatInteract();
  const { messages } = useChatMessages();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const handleSendMessage = () => {
    const content = inputValue.trim();
    if (content) {
      const message = {
        name: "user",
        type: "user_message" as const,
        output: content,
      };
      sendMessage(message, []);
      setInputValue("");
      setIsTyping(true);
    }
  };

  const renderMessage = (message: IStep) => {
    const dateOptions: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
    };
    const date = new Date(message.createdAt).toLocaleTimeString(undefined, dateOptions);
    const isUserMessage = message.name === "user";

    return (
      <div
        key={message.id}
        className={`flex items-start mb-4 ${isUserMessage ? "justify-end" : "justify-start"}`}
      >
        {/* Avatar */}
        {!isUserMessage && (
          <img
            src={botAvatar}
            alt="Bot Avatar"
            className="w-8 h-8 rounded-full mr-2"
          />
        )}

        <div
          className={`max-w-xs md:max-w-md p-4 rounded-lg ${
            isUserMessage
              ? "bg-blue-500 text-white self-end"
              : "bg-gray-200 text-black"
          }`}
        >
          <p className="text-sm">{message.output}</p>
          <small className="text-xs text-gray-500 block mt-2">{date}</small>
        </div>

        {/* Avatar on the right for the user */}
        {isUserMessage && (
          <img
            src={userAvatar}
            alt="User Avatar"
            className="w-8 h-8 rounded-full ml-2"
          />
        )}
      </div>
    );
  };

   // Handle typing state based on new messages
   useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      // If the last message is from the bot, stop typing indicator
      if (lastMessage.name !== "user") {
        setIsTyping(false);  // Stop typing indicator when bot responds
      }
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);  // Listen for changes in messages array

  
  // Scroll to the bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
      {/* Messages Container */}
      <div className="flex-1 overflow-auto p-6">
        <div className="space-y-4">
          {messages.map((message) => renderMessage(message))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start mb-4">
              <div className="bg-gray-200 text-black p-4 rounded-lg max-w-xs md:max-w-md">
                <p className="text-sm italic">Bot is typing...</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Field */}
      <div className="border-t p-4 bg-white dark:bg-gray-800 sticky bottom-0">
        <div className="flex items-center space-x-2">
          <Input
            autoFocus
            className="flex-1 rounded-lg"
            id="message-input"
            placeholder="Type a message"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyUp={(e) => {
              if (e.key === "Enter") {
                handleSendMessage();
              }
            }}
          />
          <Button
            onClick={handleSendMessage}
            type="submit"
            className="bg-blue-500 text-white rounded-lg"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
