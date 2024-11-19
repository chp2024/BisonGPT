import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState, useEffect, useRef } from "react";
import {
  useChatInteract,
  useChatMessages,
  IStep,
  IFileRef,
} from "@chainlit/react-client";
import ReactMarkdown from "react-markdown";

// Avatar image URLs (or local assets)
import userAvatar from "../assets/user_avatar.jpg";
import botAvatar from "../assets/Howard_Bison_logo.png"; // Bot's avatar image

export function Playground() {
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showIntro, setShowIntro] = useState(true); // State to control visibility of bio and recommendations
  const { sendMessage, uploadFile } = useChatInteract();
  const { messages } = useChatMessages();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content && !selectedFile) return;

    try {
      // Initialize an array for file references
      const file_refs: IFileRef[] = [];

      if (selectedFile) {
        const onProgress = (progress: number) => {
          console.log(`Upload progress: ${progress}%`);
        };

        const { promise } = uploadFile(selectedFile, onProgress);
        const fileData = await promise; // Wait for the upload to complete

        file_refs.push({ id: fileData.id });

        sendMessage({
          name: "bot",
          type: "assistant_message",
          output: `File uploaded successfully: ${selectedFile.name}`,
        });
      }

      if (content) {
        // Send text message along with file references
        sendMessage(
          {
            name: "user",
            type: "user_message",
            output: content,
          },
          file_refs
        );
      }
    } catch (error) {
      console.error("Error uploading file or sending message:", error);
      sendMessage(
        {
          name: "bot",
          type: "assistant_message",
          output: "An error occurred while processing your request.",
        },
        []
      );
    } finally {
      setInputValue("");
      setSelectedFile(null);
      setIsTyping(true);
      setShowIntro(false);
    }
  };

  const renderMessage = (message: IStep) => {
    const dateOptions: Intl.DateTimeFormatOptions = {
      hour: "2-digit",
      minute: "2-digit",
    };
    const date = new Date(message.createdAt).toLocaleTimeString(
      undefined,
      dateOptions
    );
    const isUserMessage = message.name === "user";
    const isSystemMessage = message.name === "system";

    return (
      <div
        key={message.id}
        className={`flex items-start mb-4 ${
          isUserMessage ? "justify-end" : "justify-start"
        }`}
      >
        {/* Avatar */}
        {!isUserMessage && !isSystemMessage && (
          <img
            src={botAvatar}
            alt="Bot Avatar"
            className="w-10 h-10 rounded-full mr-3"
          />
        )}

        <div
          className={`max-w-xs md:max-w-md p-4 rounded-2xl shadow-md ${
            isUserMessage
              ? "bg-blue-600 text-white rounded-br-none"
              : "bg-gray-200 text-black rounded-bl-none dark:bg-gray-700 dark:text-white"
          }`}
        >
          <ReactMarkdown className="text-sm whitespace-pre-wrap">
            {message.output}
          </ReactMarkdown>
          <small className="text-xs text-gray-400 block mt-1">{date}</small>
        </div>

        {/* Avatar on the right for the user */}
        {isUserMessage && (
          <img
            src={userAvatar}
            alt="User Avatar"
            className="w-10 h-10 rounded-full ml-3"
          />
        )}
      </div>
    );
  };

  // Handle typing state based on new messages
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];

      // Skip system messages from affecting intro visibility
      if (lastMessage.name !== "user" && lastMessage.name !== "system") {
        setIsTyping(false); // Stop typing indicator when bot responds
      }
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]); // Listen for changes in messages array

  // Scroll to the bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Predefined recommendations (tabs)
  const recommendations = [
    "Where can I get food?",
    "When is spring 2024 class registration?",
    "How many credits do I need to graduate?",
  ];

  // Handle sending predefined messages
  const handleRecommendationClick = (text: string) => {
    const message = {
      name: "user",
      type: "user_message" as const,
      output: text,
    };
    sendMessage(message, []);
    setIsTyping(true);
    setShowIntro(false); // Hide bio and recommendations when a tab is clicked
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
      {/* Bot Bio Section */}
      {showIntro && (
        <div className="flex flex-col items-center mt-10 mb-6">
          {/* Bot Avatar */}
          <img
            src={botAvatar}
            alt="Bot Avatar"
            className="w-16 h-16 rounded-full mb-2 shadow-lg"
          />
          {/* Bot Bio */}
          <p className="text-gray-700 dark:text-gray-300 text-center px-4">
            Welcome to BisonGPT, I'm here to assist you with all your Howard
            University related queries!
          </p>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-auto p-4 md:p-6 relative">
        {/* Recommendation Tabs - centered */}
        {showIntro && messages.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-wrap gap-4">
              {recommendations.map((rec, index) => (
                <Button
                  key={index}
                  onClick={() => handleRecommendationClick(rec)}
                  className="bg-gray-200 text-black dark:bg-gray-700 dark:text-white px-4 py-2 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 shadow-md"
                >
                  {rec}
                </Button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* Render Messages */}
          {messages.map((message) => renderMessage(message))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start mb-4">
              <div className="bg-gray-200 dark:bg-gray-700 text-black dark:text-white p-4 rounded-2xl max-w-xs md:max-w-md">
                <p className="text-sm italic">Processing...</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input and File Upload Section */}
      <div className="border-t border-gray-300 dark:border-gray-700 p-4 bg-white dark:bg-gray-800 sticky bottom-0">
        <div className="flex items-center space-x-2">
          {/* File Upload */}
          <input
            type="file"
            id="file-upload"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          />
          <label
            htmlFor="file-upload"
            className="cursor-pointer bg-gray-200 text-black dark:bg-gray-700 dark:text-white px-4 py-2 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 shadow-md"
          >
            Attach File
          </label>

          {/* Message Input */}
          <Input
            autoFocus
            className="flex-1 rounded-full bg-gray-100 dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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

          {/* Send Button */}
          <Button
            onClick={handleSendMessage}
            type="submit"
            className="bg-blue-600 text-white rounded-full hover:bg-blue-700"
          >
            Send
          </Button>
        </div>

        {/* Show Selected File Name */}
        {selectedFile && (
          <p className="text-sm text-gray-500 mt-2">
            Selected file: {selectedFile.name}
          </p>
        )}
      </div>
    </div>
  );
}
