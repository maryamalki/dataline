import { Fragment, useState } from "react";
import { Dialog, Transition } from "@headlessui/react";
import { api } from "../../api";
import { Spinner } from "../Spinner/Spinner";
import { enqueueSnackbar } from "notistack";
import { isAxiosError } from "axios";
import {useNavigate } from "react-router";
import { Routes } from "../../router";
import { Alert, AlertTitle } from "../Catalyst/alert";

interface NewConnectionModalFormProps {
  isOpen: boolean;
  onClose: () => void;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(" ");
}

function NewConnectionModal({ isOpen, onClose }: NewConnectionModalFormProps) {
  // const maskDSNCredentials = (dsn: string) => {
  //   const regex = /^(.*\/\/)(.*?:.*?@)(.*)$/;
  //   return dsn.replace(regex, (_, prefix, credentials, rest) => {
  //     const maskedCredentials = credentials.replace(/./g, "*");
  //     return prefix + maskedCredentials + rest;
  //   });
  // };
  // const maskedDsn = maskDSNCredentials(unmaskedDsn);

  const [unmaskedDsn, setUnmaskedDsn] = useState("");
  const [connectionName, setConnectionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const clearInputs = () => {
    setUnmaskedDsn("");
    setConnectionName("");
  };

  const handleDSNChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setUnmaskedDsn(value);
  };

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setConnectionName(value);
  };

  const handleCreateTestConnection = async () => {
    if (isLoading) return;
    return navigate(Routes.SampleConnectionSetup);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Enable loading state
    setIsLoading(true);
    try {
      const res = await api.createConnection(unmaskedDsn, connectionName);
      if (res.status !== "ok") {
        enqueueSnackbar({
          variant: "error",
          message: "Error creating connection",
        });
        setIsLoading(false);
        return;
      }
    } catch (exception) {
      if (isAxiosError(exception) && exception.response?.status === 409) {
        // Connection already exists, skip creation but don't close or clear modal
        enqueueSnackbar({
          variant: "info",
          message: "Connection already exists, skipping creation",
        });
        setIsLoading(false);
        return;
      } else {
        enqueueSnackbar({
          variant: "error",
          message: "Error creating connection",
        });
        setIsLoading(false);
        return;
      }
    }

    setIsLoading(false);
    clearInputs();
    onClose();
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10 md:ml-72" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto h-[calc(100%-4rem)] lg:pl-72 lg:h-full w-full">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-gray-900 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-xl sm:p-6">
                
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}

export default NewConnectionModal;
